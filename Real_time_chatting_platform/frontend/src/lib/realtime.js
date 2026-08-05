/**
 * WebSocket client for real-time chat.
 *
 * Route: GET /ws/{conversation_id}?token=<access token>
 *
 * Auth is a query parameter for the same reason the SSE stream takes one — the
 * browser WebSocket constructor accepts no custom headers, so there is nowhere
 * else to put a bearer credential. The handshake verifies the token and active
 * membership; failures close with an application code rather than a normal 1000:
 *
 *   4401  token missing / invalid / expired  -> refresh and reopen
 *   4403  not a member of this conversation  -> do not retry, it will not change
 *
 * Server -> client frames:
 *   { type: "message",      payload: MessageResponse }
 *   { type: "typing_start", conversation_id, user_id }
 *   { type: "typing_stop",  conversation_id, user_id }
 *   { type: "error",        code, message }
 *
 * Client -> server frames:
 *   { type: "typing_start" } | { type: "typing_stop" }
 */

import { API_BASE_URL } from "./apiClient";

export const WS_UNAUTHORIZED = 4401;
export const WS_FORBIDDEN = 4403;

/** ws:// for http://, wss:// for https:// — matching the API's scheme. */
export function realtimeUrl(token, conversationId) {
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}/ws/${conversationId}?token=${encodeURIComponent(token)}`;
}

/**
 * Minimal reconnecting WebSocket.
 *
 * Unlike EventSource, the WebSocket API has no built-in retry, so the backoff
 * below has to be written by hand — which is exactly why the notification
 * stream has none of this code.
 *
 * @param {object}   opts
 * @param {string}   opts.token           access token
 * @param {string}   opts.conversationId
 * @param {Function} opts.onMessage       receives one parsed frame
 * @param {Function} opts.onStateChange   "connecting" | "open" | "closed" | "error" | "forbidden"
 * @param {Function} opts.onAuthExpired   called on a 4401 close, to mint a fresh token
 * @returns {{close: () => void, send: (frame: object) => boolean}}
 */
export function connectRealtime({
  token,
  conversationId,
  onMessage,
  onStateChange,
  onAuthExpired,
}) {
  let socket = null;
  let attempt = 0;
  let retryTimer = null;
  let closedByCaller = false;

  function open() {
    socket = new WebSocket(realtimeUrl(token, conversationId));
    onStateChange?.("connecting");

    socket.onopen = () => {
      attempt = 0;
      onStateChange?.("open");
    };

    socket.onmessage = (event) => {
      try {
        onMessage?.(JSON.parse(event.data));
      } catch {
        /* ignore a malformed frame rather than tearing down a working socket */
      }
    };

    socket.onclose = (event) => {
      if (closedByCaller) return;

      // Not a member. Retrying cannot help — only a membership change would,
      // and that arrives through a different channel.
      if (event.code === WS_FORBIDDEN) {
        onStateChange?.("forbidden");
        return;
      }

      // Expired token: ask for a fresh one. The caller re-runs its effect with
      // the new token, which opens a new socket — so no retry is scheduled here,
      // otherwise two would race.
      if (event.code === WS_UNAUTHORIZED) {
        onStateChange?.("error");
        onAuthExpired?.();
        return;
      }

      onStateChange?.("closed");
      // Exponential backoff, capped at 30s.
      const delay = Math.min(1000 * 2 ** attempt, 30_000);
      attempt += 1;
      retryTimer = setTimeout(open, delay);
    };

    socket.onerror = () => onStateChange?.("error");
  }

  open();

  return {
    /** @returns {boolean} false if the socket was not open, so the frame was dropped. */
    send(frame) {
      if (socket?.readyState !== WebSocket.OPEN) return false;
      socket.send(JSON.stringify(frame));
      return true;
    },
    close() {
      closedByCaller = true;
      clearTimeout(retryTimer);
      socket?.close();
    },
  };
}
