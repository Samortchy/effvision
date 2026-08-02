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
 * ⚠️ PENDING BACKEND — no send-message endpoint exists.
 *
 * Verified on 2026-07-30: api/routes/messages.py has only DELETE /{message_id}
 * and GET /{conversation_id}/search. There is no POST anywhere that creates a
 * message, no api/websocket/ package, and infrastructure/websocket/broadcaster.py
 * imports a connection_manager module that has not been written yet. The repo
 * layer *can* create messages (SQLAlchemyMessageRepository.create) — nothing is
 * wired up to it.
 *
 * Left as an explicit throw rather than a silent no-op so the UI can show the
 * real reason instead of pretending a message was delivered.
 */
export async function sendMessage() {
  throw new Error(
    "Sending is not available yet: the backend has no send-message endpoint or WebSocket layer.",
  );
}

/**
 * ⚠️ PENDING BACKEND — no endpoint lists a conversation's members.
 *
 * ConversationMemberResponse exists in application/dto/conversation_dto.py but
 * no route returns it, so the members panel is fed from locally known users
 * (see chatStore.userCache). When GET /conversations/{id}/members lands, swap
 * this in and the panel works unchanged.
 */
export async function fetchMembers() {
  throw new Error("Listing conversation members is not supported by the backend yet.");
}
