/**
 * Framework-free token holder.
 *
 * Lives outside Zustand on purpose: the axios interceptor and the auth store
 * both need it, and importing the store from the client (and the client from
 * the store) would be a cycle. Keeping the raw tokens here leaves the stores
 * to hold *user-facing* state only.
 *
 * Storage split:
 *   - access token  -> memory only. Gone on reload, which is the point; it is
 *     never exposed to another tab or to anything that can read localStorage.
 *   - refresh token -> localStorage, so a reload can recover a session. The
 *     backend hands it to the client as JSON (no httpOnly cookie), so there is
 *     nowhere better to put it; this is the tradeoff that design forces.
 */

const REFRESH_TOKEN_KEY = "effvision.refresh_token";

let accessToken = null;

/** Bumped on every token change so useSyncExternalStore subscribers re-read. */
let version = 0;
const listeners = new Set();

function emit() {
  version += 1;
  for (const listener of listeners) listener();
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Snapshot must be a primitive: the token string itself is the identity. */
export function getAccessToken() {
  return accessToken;
}

export function getVersion() {
  return version;
}

export function getRefreshToken() {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    // Private-mode Safari and friends throw rather than return null.
    return null;
  }
}

/**
 * Store a fresh pair. The backend rotates on every refresh (the old refresh
 * token is dead the moment it is used), so both halves must land together.
 */
export function setTokens({ access_token, refresh_token }) {
  accessToken = access_token ?? null;
  try {
    if (refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
  } catch {
    /* non-fatal: the session simply will not survive a reload */
  }
  emit();
}

export function clearTokens() {
  accessToken = null;
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    /* ignore */
  }
  emit();
}

/**
 * Called when the refresh chain itself fails — the session is unrecoverable
 * and the app has to fall back to the login screen. The auth store registers
 * here rather than the client importing the store.
 */
const unauthorizedHandlers = new Set();

export function onUnauthorized(handler) {
  unauthorizedHandlers.add(handler);
  return () => unauthorizedHandlers.delete(handler);
}

export function notifyUnauthorized() {
  clearTokens();
  for (const handler of unauthorizedHandlers) handler();
}
