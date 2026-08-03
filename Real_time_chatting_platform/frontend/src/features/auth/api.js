import apiClient from "../../lib/apiClient";

/**
 * POST /auth/register
 * RegisterRequest  { username, email, password }  -> 201 RegisterResponse { id, username, email }
 *
 * Note it returns the *user*, not tokens — registering does not sign you in,
 * so the UI has to follow it with a login call.
 */
export async function registerRequest({ username, email, password }) {
  const { data } = await apiClient.post("/auth/register", {
    username,
    email,
    password,
  });
  return data;
}

/**
 * POST /auth/login
 * LoginRequest  { identifier, password }   <- identifier is email OR username
 * TokenResponse { access_token, refresh_token, token_type }
 *
 * Landed in the backend on 2026-08-02 (api/routes/auth.py + use_cases/auth/login.py).
 * Bad credentials come back as 401 with a single generic message — the backend
 * will not tell you whether it was the identifier or the password that was
 * wrong, so don't try to render a field-specific error from it.
 */
export async function loginRequest({ identifier, password }) {
  const { data } = await apiClient.post("/auth/login", { identifier, password });
  return data;
}

/** POST /auth/refresh — rotates; the old refresh token dies on use. */
export async function refreshRequest(refresh_token) {
  const { data } = await apiClient.post("/auth/refresh", { refresh_token });
  return data;
}

/** POST /auth/logout -> 204. Takes the refresh token in the body, not a header. */
export async function logoutRequest(refresh_token) {
  await apiClient.post("/auth/logout", { refresh_token });
}

/** GET /users/me -> UserProfileResponse */
export async function fetchMe() {
  const { data } = await apiClient.get("/users/me");
  return data;
}
