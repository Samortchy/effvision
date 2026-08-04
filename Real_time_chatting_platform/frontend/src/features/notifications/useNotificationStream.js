import { useEffect, useRef, useState } from "react";

import apiClient, { API_BASE_URL } from "../../lib/apiClient";
import { useAccessToken } from "../../lib/useAccessToken";
import { useNotificationStore } from "../../stores/notificationStore";

/** Reconnect backoff: 1s, 2s, 4s … capped. */
const RETRY_BASE_MS = 1000;
const RETRY_MAX_MS = 30000;

/**
 * Subscribe to GET /notifications/stream over native EventSource.
 *
 * Three backend facts drive the shape of this hook:
 *
 * 1. Auth is a one-shot TICKET in the query string, not the access token.
 *    EventSource cannot set headers, so the credential has to live in the URL —
 *    where it lands in access logs, proxy logs and browser history. So the thing
 *    put there is deliberately cheap: POST /auth/stream-ticket (authenticated by
 *    header, like everything else) returns a ticket that dies on first use and
 *    expires in seconds. A ticket scraped out of a log is already spent.
 *
 * 2. Reconnection is mostly the browser's job. The server emits an `id` on every
 *    event (an ISO timestamp) and parses the Last-Event-ID that EventSource
 *    replays as a resume cursor, so a dropped connection recovers without losing
 *    events.
 *
 * 3. ...but a ticket is single-use, so the browser's own retry — which reuses the
 *    original URL, spent ticket and all — gets a 401. Per the EventSource spec a
 *    non-2xx fails the connection permanently: readyState goes to CLOSED and the
 *    browser stops. That is the case this hook covers, and the only one: when the
 *    browser gives up, mint a fresh ticket and open a new stream. Last-Event-ID is
 *    resent by the new EventSource, so nothing is missed across the gap.
 *
 * Expired *access* tokens need no handling here: minting a ticket is an ordinary
 * apiClient call, so the 401-refresh-retry interceptor covers it, and a session
 * that is genuinely dead signs the user out through the same path.
 */
export function useNotificationStream(enabled) {
  // The token's identity is irrelevant now that it never reaches the URL — only
  // whether we have one. Depending on the string itself would tear the stream
  // down and rebuild it on every routine token rotation.
  const hasToken = Boolean(useAccessToken());
  const pushEvent = useNotificationStore((state) => state.pushEvent);
  const setConnection = useNotificationStore((state) => state.setConnection);

  // Bumped to force the effect to re-run and open a fresh stream.
  const [attempt, setAttempt] = useState(0);
  const failuresRef = useRef(0);

  useEffect(() => {
    if (!enabled || !hasToken) {
      setConnection("idle");
      return undefined;
    }

    let cancelled = false;
    let source = null;
    let retryTimer = null;

    const scheduleRetry = () => {
      if (cancelled || retryTimer) return;
      const delay = Math.min(RETRY_BASE_MS * 2 ** failuresRef.current, RETRY_MAX_MS);
      failuresRef.current += 1;
      retryTimer = setTimeout(() => {
        retryTimer = null;
        if (!cancelled) setAttempt((n) => n + 1);
      }, delay);
    };

    const handle = (event) => {
      try {
        pushEvent(JSON.parse(event.data));
      } catch {
        // A malformed frame should not tear down a working stream.
      }
    };

    (async () => {
      setConnection("connecting");

      let ticket;
      try {
        const { data } = await apiClient.post("/auth/stream-ticket");
        ticket = data.ticket;
      } catch {
        // Network blip, or a session the interceptor could not refresh. Either
        // way: back off and try again rather than leaving the bell dead.
        if (!cancelled) {
          setConnection("error");
          scheduleRetry();
        }
        return;
      }

      // The effect may have been torn down while the ticket was in flight.
      if (cancelled) return;

      source = new EventSource(
        `${API_BASE_URL}/notifications/stream?ticket=${encodeURIComponent(ticket)}`,
      );

      // Separate listeners per type: the server sets the SSE `event:` field from
      // event_category, so a bare onmessage handler would never fire.
      source.addEventListener("notification", handle);
      source.addEventListener("system_announcement", handle);
      source.addEventListener("open", () => {
        failuresRef.current = 0;
        setConnection("open");
      });

      source.onerror = () => {
        // Still CONNECTING means the browser is retrying by itself. That retry
        // replays a spent ticket and will fail, but letting it run costs one
        // request and keeps the browser's own resume behaviour intact.
        if (source.readyState !== EventSource.CLOSED) {
          setConnection("connecting");
          return;
        }

        setConnection("error");
        scheduleRetry();
      };
    })();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (source) {
        source.removeEventListener("notification", handle);
        source.removeEventListener("system_announcement", handle);
        source.close();
      }
    };
  }, [enabled, hasToken, attempt, pushEvent, setConnection]);
}
