import apiClient from "../../lib/apiClient";

/**
 * GET /users/search?q=&limit=&offset= -> UserSummary[]
 * UserSummary = { id, username, display_name, avatar_url, status }
 *
 * `q` is required and must be 1–50 chars (422 otherwise), so callers should
 * skip the request entirely on an empty box.
 */
export async function searchUsers({ q, limit = 20, offset = 0 }) {
  const { data } = await apiClient.get("/users/search", {
    params: { q, limit, offset },
  });
  return data;
}
