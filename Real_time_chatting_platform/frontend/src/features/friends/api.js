import apiClient from "../../lib/apiClient";

/** GET /friends -> UserSummary[], alphabetical. */
export async function fetchFriends() {
  const { data } = await apiClient.get("/friends");
  return data;
}

/**
 * GET /friends/requests?direction=incoming|outgoing -> FriendRequestResponse[]
 *
 * Pending only. Each row embeds `user` — the *other* party, so the sender on an
 * incoming request and the recipient on an outgoing one.
 */
export async function fetchFriendRequests(direction = "incoming") {
  const { data } = await apiClient.get("/friends/requests", { params: { direction } });
  return data;
}

/**
 * POST /friends/requests { user_id } -> 201 FriendRequestResponse
 *
 * 409 covers three distinct situations, and the message says which: already
 * friends, you already asked, or they already asked you.
 */
export async function sendFriendRequest(userId) {
  const { data } = await apiClient.post("/friends/requests", { user_id: userId });
  return data;
}

/** POST /friends/requests/{id}/accept -> FriendRequestResponse. Creates the friendship. */
export async function acceptFriendRequest(requestId) {
  const { data } = await apiClient.post(`/friends/requests/${requestId}/accept`);
  return data;
}

/** POST /friends/requests/{id}/decline -> FriendRequestResponse. They may ask again later. */
export async function declineFriendRequest(requestId) {
  const { data } = await apiClient.post(`/friends/requests/${requestId}/decline`);
  return data;
}

/** DELETE /friends/{user_id} -> 204. Symmetric — ends for both sides. */
export async function removeFriend(userId) {
  await apiClient.delete(`/friends/${userId}`);
}
