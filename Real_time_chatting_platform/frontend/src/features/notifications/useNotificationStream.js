import { useEffect, useRef } from "react";

import { API_BASE_URL, refreshAccessToken } from "../../lib/apiClient";
import { useAccessToken } from "../../lib/useAccessToken";
import { useNotificationStore } from "../../stores/notificationStore";

/**
 * Subscribe to GET /notifications/stream over native EventSource.
 *
 * Two backend quirks drive the shape of this hook:
 *
 * 1. Auth is a QUERY PARAM, not a header. EventSource cannot set headers, so
 *    the route accepts ?token=<access token> (api/dependencies/auth.py::
 *    get_current_user_sse). The header still wins when both are present, but a
 *    browser can only ever use the query param.
 *
 * 2. Reconnection is the browser's job, not ours. The server emits an `id` on
 *    every event (an ISO timestamp) and parses the Last-Event-ID that
 *    EventSource replays on reconnect as a resume cursor, so a dropped
 *    connection recovers without losing events — and without any retry code
 *    here.
 *
 * The one case the browser genuinely cannot handle: access tokens expire after
 * 15 minutes (config.access_token_expire_minutes), and a stream that dies on an
 * expired token gets a 401 *response*. Per the EventSource spec a non-2xx
 * response fails the connection permanently — readyState goes to CLOSED and the
 * browser never retries. So the only reconnect logic here is "if the browser
 * gave up, mint a fresh token and reopen", which is exactly the gap it cannot
 * cover itself.
 */
export function useNotificationStream(enabled) {
  const token = useAccessToken();
  const pushEvent = useNotificationStore((state) => state.pushEvent);
  const setConnection = useNotificationStore((state) => state.setConnection);

  // Guards against two refresh attempts racing when the stream flaps.
  const recoveringRef = useRef(false);

  useEffect(() => {
    if (!enabled || !token) {
      setConnection("idle");
      return undefined;
    }

    const url = `${API_BASE_URL}/notifications/stream?token=${encodeURIComponent(token)}`;
    const source = new EventSource(url);
    setConnection("connecting");

    const handle = (event) => {
      try {
        pushEvent(JSON.parse(event.data));
      } catch {
        // A malformed frame should not tear down a working stream.
      }
    };

    // Separate listeners per type: the server sets the SSE `event:` field from
    // event_category, so a bare onmessage handler would never fire.
    source.addEventListener("notification", handle);
    source.addEventListener("system_announcement", handle);
    source.addEventListener("open", () => {
      recoveringRef.current = false;
      setConnection("open");
    });

    source.onerror = async () => {
      // Still CONNECTING means the browser is already retrying by itself —
      // leave it alone, that is the behaviour we want.
      if (source.readyState !== EventSource.CLOSED) {
        setConnection("connecting");
        return;
      }

      setConnection("error");
      if (recoveringRef.current) return;
      recoveringRef.current = true;

      try {
        // Rotates the pair and bumps the session version, which re-runs this
        // effect with a fresh token and opens a new stream.
        await refreshAccessToken();
      } catch {
        // Unrecoverable — the 401 handler will have signed the user out.
      }
    };

    return () => {
      source.removeEventListener("notification", handle);
      source.removeEventListener("system_announcement", handle);
      source.close();
    };
  }, [enabled, token, pushEvent, setConnection]);
}
