/**
 * WebSocket wrapper for real-time messaging — NOT CONNECTED.
 *
 * Backend state as verified on 2026-07-30:
 *   - There is no api/websocket/ package. api/ contains only routes/ and
 *     dependencies/, and no route anywhere declares a @router.websocket.
 *   - infrastructure/websocket/ holds broadcaster.py alone, and that file
 *     imports infrastructure.websocket.connection_manager, which does not
 *     exist — so even the server-side broadcast path cannot import today.
 *   - domain/repositories/broadcaster.py defines the interface it is meant to
 *     satisfy.
 *
 * So there is no URL to connect to and no message envelope to agree on yet.
 * Rather than guess a protocol and write code that silently retries against a
 * 404 forever, this stays inert behind an explicit opt-in.
 *
 * To turn it on once the backend lands:
 *   1. Confirm the route path and the auth carrier. A browser WebSocket cannot
 *      set an Authorization header either, so it will likely need ?token= in
 *      the query string, the same exception the SSE stream makes.
 *   2. Confirm the inbound envelope and map it onto chatStore.receiveMessage,
 *      which already takes a MessageResponse-shaped object.
 *   3. Set VITE_ENABLE_WEBSOCKET=true and call connectRealtime() from
 *      AppLayout alongside useNotificationStream.
 */

import { API_BASE_URL } from "./apiClient";

export const REALTIME_ENABLED = import.meta.env.VITE_ENABLE_WEBSOCKET === "true";

/** Best guess at the eventual URL; unused until the route exists. */
export function realtimeUrl(token, path = "/ws") {
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}${path}?token=${encodeURIComponent(token)}`;
}

/**
 * Minimal reconnecting WebSocket.
 *
 * Unlike EventSource, the WebSocket API has no built-in retry, so backoff has
 * to be written by hand — which is exactly why the notification stream does not
 * have any of this code.
 *
 * @returns {{close: () => void}}
 */
export function connectRealtime({ token, onMessage, onStateChange, path = "/ws" }) {
  if (!REALTIME_ENABLED) {
    onStateChange?.("disabled");
    return { close() {} };
  }

  let socket = null;
  let attempt = 0;
  let retryTimer = null;
  let closedByCaller = false;

  function open() {
    socket = new WebSocket(realtimeUrl(token, path));
    onStateChange?.("connecting");

    socket.onopen = () => {
      attempt = 0;
      onStateChange?.("open");
    };

    socket.onmessage = (event) => {
      try {
        onMessage?.(JSON.parse(event.data));
      } catch {
        /* ignore malformed frames */
      }
    };

    socket.onclose = () => {
      if (closedByCaller) return;
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
    close() {
      closedByCaller = true;
      clearTimeout(retryTimer);
      socket?.close();
    },
  };
}
