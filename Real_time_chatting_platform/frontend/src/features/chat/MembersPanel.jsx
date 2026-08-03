import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Alert, Avatar, Button, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { shortId } from "../../lib/formatters";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";

const ROLES = ["owner", "admin", "member"];

/**
 * Group membership management: leave, change role, remove member.
 *
 * The three actions are wired to the real endpoints and work. What is missing
 * is the *read* side: no route returns a conversation's members
 * (ConversationMemberResponse is defined but never returned by anything), so
 * this panel can only list users this browser already knows — the conversation
 * peer and anyone seen in search. Swap in chatApi.fetchMembers once
 * GET /conversations/{id}/members exists and the rest of this component is
 * unchanged.
 *
 * Roles are also unknown for the same reason, so the role control shows no
 * current value; it only issues changes.
 */
export default function MembersPanel({ conversationId, onClose }) {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.user);
  const conversation = useChatStore((state) =>
    state.conversations.find((c) => c.id === conversationId),
  );
  const userCache = useChatStore((state) => state.userCache);
  const leaveConversation = useChatStore((state) => state.leaveConversation);
  const changeMemberRole = useChatStore((state) => state.changeMemberRole);
  const removeMember = useChatStore((state) => state.removeMember);

  const [busyUserId, setBusyUserId] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [leaving, setLeaving] = useState(false);

  // Everything we can honestly claim is in this conversation.
  const known = [
    currentUser,
    conversation?.peer,
    ...(conversation?.type !== "private"
      ? Object.values(userCache).filter(
          (u) => u.id !== currentUser?.id && u.id !== conversation?.peer?.id,
        )
      : []),
  ].filter(Boolean);

  async function withBusy(userId, action, successMessage) {
    setBusyUserId(userId);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(successMessage);
    } catch (err) {
      setError(describeApiError(err, "That action failed."));
    } finally {
      setBusyUserId(null);
    }
  }

  async function handleLeave() {
    setLeaving(true);
    setError(null);
    try {
      await leaveConversation(conversationId);
      navigate("/", { replace: true });
    } catch (err) {
      // 400 = private conversation, 409 = you are the last owner.
      setError(describeApiError(err, "Could not leave this conversation."));
      setLeaving(false);
    }
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-l border-edge bg-surface-sunken">
      <header className="flex items-center justify-between border-b border-edge px-4 py-3">
        <h2 className="text-sm font-semibold text-white">Members</h2>
        <Button variant="ghost" onClick={onClose} aria-label="Close members panel">
          ✕
        </Button>
      </header>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        <Alert tone="info" className="text-xs leading-relaxed">
          No endpoint lists members yet, so this shows only people this browser
          has seen. The actions below are live and hit the real API.
        </Alert>

        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="info">{notice}</Alert> : null}

        <ul className="space-y-2">
          {known.map((member) => {
            const isSelf = member.id === currentUser?.id;
            const busy = busyUserId === member.id;

            return (
              <li
                key={member.id}
                className="rounded-lg border border-edge bg-surface p-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <Avatar user={member} size={30} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-slate-100">
                      {member.display_name || member.username || shortId(member.id)}
                      {isSelf ? (
                        <span className="ml-1 text-xs text-slate-500">(you)</span>
                      ) : null}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      @{member.username}
                    </p>
                  </div>
                  {busy ? <Spinner /> : null}
                </div>

                {!isSelf ? (
                  <div className="mt-2 flex items-center gap-2">
                    <select
                      defaultValue=""
                      disabled={busy}
                      onChange={(event) => {
                        const role = event.target.value;
                        if (!role) return;
                        event.target.value = "";
                        withBusy(
                          member.id,
                          () => changeMemberRole(conversationId, member.id, role),
                          `Role updated to ${role}.`,
                        );
                      }}
                      className="flex-1 rounded-md border border-edge bg-surface-sunken px-2 py-1 text-xs text-slate-200 focus:border-accent focus:outline-none"
                      aria-label={`Change role for ${member.username}`}
                    >
                      <option value="">Set role…</option>
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>

                    <Button
                      variant="danger"
                      disabled={busy}
                      className="px-2 py-1 text-xs"
                      onClick={() =>
                        withBusy(
                          member.id,
                          () => removeMember(conversationId, member.id),
                          `${member.username} removed.`,
                        )
                      }
                    >
                      Remove
                    </Button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="border-t border-edge p-3">
        <Button
          variant="outline"
          className="w-full"
          onClick={handleLeave}
          disabled={leaving || conversation?.type === "private"}
        >
          {leaving ? <Spinner /> : null}
          Leave conversation
        </Button>
        {conversation?.type === "private" ? (
          <p className="mt-2 text-xs text-slate-500">
            Private conversations cannot be left (the API returns 400).
          </p>
        ) : null}
      </div>
    </aside>
  );
}
