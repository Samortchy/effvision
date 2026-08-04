import axios from "axios";

import {
  getAccessToken,
  getRefreshToken,
  notifyUnauthorized,
  setTokens,
} from "./session";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Bare instance for the refresh call itself. It deliberately has no
 * interceptors: if /auth/refresh returned 401 through the main client it would
 * try to refresh in order to retry the refresh, forever.
 */
const bareClient = axios.create({ baseURL: API_BASE_URL });

export const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * In-flight refresh, shared by every caller.
 *
 * This matters more than usual here: the backend *rotates* refresh tokens, so
 * two concurrent 401s each firing their own /auth/refresh would race — the
 * second would present a token the first had already consumed and burned, and
 * the whole session would be invalidated. Collapsing them into one promise
 * means N waiting requests all resume on a single rotation.
 */
let refreshPromise = null;

function runRefresh() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh_token = getRefreshToken();
    if (!refresh_token) throw new Error("No refresh token available");

    const { data } = await bareClient.post("/auth/refresh", { refresh_token });
    setTokens(data);
    return data.access_token;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

/** Exported so the auth store can restore a session on boot from the refresh token. */
export { runRefresh as refreshAccessToken };

/** Endpoints that must never trigger the refresh-and-retry dance. */
const AUTH_PATHS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

function isAuthPath(url = "") {
  return AUTH_PATHS.some((path) => url.startsWith(path));
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;

    if (
      response?.status !== 401 ||
      !config ||
      config._retried ||
      isAuthPath(config.url)
    ) {
      return Promise.reject(error);
    }

    // Retry exactly once. _retried is set before awaiting so a retry that
    // itself 401s (revoked user, dead session) falls straight through.
    config._retried = true;

    try {
      const accessToken = await runRefresh();
      // Mutate rather than spread: config.headers is an AxiosHeaders instance,
      // and flattening it to a plain object loses its normalisation.
      config.headers.Authorization = `Bearer ${accessToken}`;
      return apiClient(config);
    } catch {
      notifyUnauthorized();
      return Promise.reject(error);
    }
  },
);

/** Pull a human-readable message out of FastAPI's error shapes. */
export function describeApiError(error, fallback = "Something went wrong.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  // 422 from Pydantic: detail is a list of {loc, msg, type}.
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.at(-1) : null;
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join(", ");
  }
  if (error?.message === "Network Error") {
    return "Cannot reach the server. Is the backend running, and does it allow this origin (CORS)?";
  }
  return fallback;
}

export default apiClient;
