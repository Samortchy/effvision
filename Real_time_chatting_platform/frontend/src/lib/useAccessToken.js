import { useSyncExternalStore } from "react";

import { getAccessToken, subscribe } from "./session";

/**
 * Read the in-memory access token reactively.
 *
 * The token lives in a plain module so the axios interceptor can reach it, but
 * the SSE stream has to *re-open* whenever it rotates (the token is baked into
 * the stream URL). useSyncExternalStore bridges the two.
 */
export function useAccessToken() {
  return useSyncExternalStore(subscribe, getAccessToken, () => null);
}
