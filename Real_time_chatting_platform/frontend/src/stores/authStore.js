import { create } from "zustand";

import {
  clearTokens,
  getRefreshToken,
  onUnauthorized,
  setTokens,
} from "../lib/session";
import { refreshAccessToken } from "../lib/apiClient";
import {
  fetchMe,
  loginRequest,
  logoutRequest,
  registerRequest,
} from "../features/auth/api";

/**
 * Auth session state. The tokens themselves live in lib/session.js — this
 * store holds the parts the UI actually renders: who you are and whether the
 * app is still deciding.
 *
 * status:
 *   "unknown"       - bootstrap has not run; render a splash, not the login page
 *   "authenticated" - `user` is populated
 *   "anonymous"     - no usable session
 */
export const useAuthStore = create((set, get) => ({
  user: null,
  status: "unknown",
  error: null,

  /**
   * Recover a session on page load. The access token is memory-only so it is
   * always gone after a reload; the refresh token in localStorage is what makes
   * this possible. A failure here is normal (expired/rotated-away token), not
   * an error worth showing.
   */
  bootstrap: async () => {
    if (!getRefreshToken()) {
      set({ status: "anonymous", user: null });
      return;
    }

    try {
      await refreshAccessToken();
      const user = await fetchMe();
      set({ user, status: "authenticated", error: null });
    } catch {
      clearTokens();
      set({ user: null, status: "anonymous" });
    }
  },

  login: async ({ identifier, password }) => {
    set({ error: null });
    const tokens = await loginRequest({ identifier, password });
    setTokens(tokens);
    const user = await fetchMe();
    set({ user, status: "authenticated" });
    return user;
  },

  /**
   * Register then sign in. /auth/register returns the user but no tokens, so
   * the second call is required — and it currently hits the missing login
   * route, meaning registration succeeds and then sign-in fails. The UI says so
   * rather than looking like the registration itself broke.
   */
  register: async ({ username, email, password }) => {
    set({ error: null });
    const created = await registerRequest({ username, email, password });
    await get().login({ identifier: username, password });
    return created;
  },

  logout: async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) await logoutRequest(refreshToken);
    } catch {
      // Revoking server-side is best-effort; the local session goes either way.
    }
    clearTokens();
    set({ user: null, status: "anonymous", error: null });
  },

  /** Hard sign-out triggered by an unrecoverable 401 in the interceptor. */
  sessionExpired: () => {
    set({
      user: null,
      status: "anonymous",
      error: "Your session expired. Please sign in again.",
    });
  },

  clearError: () => set({ error: null }),
}));

// Bridge the framework-free session module back into the store.
onUnauthorized(() => useAuthStore.getState().sessionExpired());
