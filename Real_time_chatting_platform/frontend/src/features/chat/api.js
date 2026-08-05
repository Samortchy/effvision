import apiClient from "../../lib/apiClient";

/** POST /conversations/private { recipient_id } -> ConversationResponse */
export async function startPrivateConversation(recipientId) {
  const { data } = await apiClient.post("/conversations/private", {
    recipient_id: recipientId,
  });
  return data;
}

/**
 * GET /conversations/{id}/messages?before=&limit=
 *
 * Cursor pagination, not pages. Two things verified against
 * infrastructure/repositories/message_repository_sqla.py:
 *   1. Results come back NEWEST FIRST (order_by created_at.desc()).
 *   2. `before` is a strict `<`, so passing the oldest message's created_at
 *      yields the next older window with no duplicated boundary row.
 * `limit` defaults to 20 server-side and is capped at 100.
 *
 * @param {string}  conversationId
 * @param {object}  opts
 * @param {string} [opts.before]  ISO-8601 timestamp; omit for the newest page.
 * @param {number} [opts.limit]
 * @returns {Promise<Array>} MessageResponse[], newest first.
 */
export async function fetchMessageHistory(conversationId, { before, limit } = {}) {
  const params = {};
  if (before) params.before = before;
  if (limit) params.limit = limit;

  const { data } = await apiClient.get(
    `/conversations/${conversationId}/messages`,
    { params },
  );
  return data;
}

/** DELETE /messages/{message_id} -> 204. Soft delete; sender only (403 otherwise). */
export async function deleteMessage(messageId) {
  await apiClient.delete(`/messages/${messageId}`);
}

/** GET /messages/{conversation_id}/search?q=&limit=&offset= — offset-based here, unlike history. */
export async function searchMessages(conversationId, { q, limit = 20, offset = 0 }) {
  const { data } = await apiClient.get(`/messages/${conversationId}/search`, {
    params: { q, limit, offset },
  });
  return data;
}

/** POST /conversations/{id}/leave -> 204 */
export async function leaveConversation(conversationId) {
  await apiClient.post(`/conversations/${conversationId}/leave`);
}

/**
 * PATCH /conversations/{id}/members/{target_user_id}/role  { role } -> 204
 * role is one of "owner" | "admin" | "member" (domain/entities/conversation_member.py).
 */
export async function changeMemberRole(conversationId, targetUserId, role) {
  await apiClient.patch(
    `/conversations/${conversationId}/members/${targetUserId}/role`,
    { role },
  );
}

/** DELETE /conversations/{id}/members/{target_user_id} -> 204 */
export async function removeMember(conversationId, targetUserId) {
  await apiClient.delete(
    `/conversations/${conversationId}/members/${targetUserId}`,
  );
}

/**
 * POST /messages/{conversation_id}  { content } -> 201 MessageResponse
 *
 * The server broadcasts the new message to everyone in the room *except* the
 * sender, so this response is the only copy our own client gets — it has to be
 * folded into the thread by the caller.
 *
 * 403 = you are not a member, 404 = no such conversation.
 */
export async function sendMessage(conversationId, content) {
  const { data } = await apiClient.post(`/messages/${conversationId}`, { content });
  return data;
}

/** PATCH /messages/{message_id}  { content } -> MessageResponse. Sender only (403 otherwise). */
export async function editMessage(messageId, content) {
  const { data } = await apiClient.patch(`/messages/${messageId}`, { content });
  return data;
}

/** GET /conversations -> ConversationResponse[], newest activity first. */
export async function fetchMyConversations() {
  const { data } = await apiClient.get("/conversations");
  return data;
}

/** GET /conversations/{id}/members -> ConversationMemberResponse[]. Active members only; 403 if you are not one. */
export async function fetchMembers(conversationId) {
  const { data } = await apiClient.get(`/conversations/${conversationId}/members`);
  return data;
}

/**
 * POST /conversations/group  { name, description?, member_ids[] } -> 201 ConversationResponse
 *
 * The caller becomes the group's owner. `member_ids` may be empty — a group can
 * be created first and filled from the members panel afterwards.
 */
export async function createGroup({ name, description, memberIds = [] }) {
  const { data } = await apiClient.post("/conversations/group", {
    name,
    description: description || null,
    member_ids: memberIds,
  });
  return data;
}

/**
 * POST /conversations/{id}/members  { user_id, role } -> 201 ConversationMemberResponse
 *
 * Owners and admins only (403 otherwise). 409 if the user is already in.
 * `role` is "member" or "admin" — granting ownership goes through
 * changeMemberRole, which enforces the last-owner rule.
 */
export async function addMember(conversationId, userId, role = "member") {
  const { data } = await apiClient.post(`/conversations/${conversationId}/members`, {
    user_id: userId,
    role,
  });
  return data;
}

/** GET /conversations/public -> ConversationResponse. The single global room. */
export async function fetchPublicConversation() {
  const { data } = await apiClient.get("/conversations/public");
  return data;
}

/** POST /conversations/public/join -> 201 ConversationMemberResponse. 409 if already joined. */
export async function joinPublicConversation() {
  const { data } = await apiClient.post("/conversations/public/join");
  return data;
}
