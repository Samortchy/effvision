import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Alert, Avatar, Button, Spinner } from "../../components/ui";
import { describeApiError } from "../../lib/apiClient";
import { shortId } from "../../lib/formatters";
import { fetchMembers } from "./api";
import UserPicker from "../users/UserPicker";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";

const ROLES = ["owner", "admin", "member"];

/**
 * Group membership management: list, leave, change role, remove member.
 *
 * The roster comes from GET /conversations/{id}/members, which returns active
 * members with their real roles. Names are not in that payload — a member row
 * carries a user_id — so they are resolved through chatStore.userCache and fall
 * back to a short id for anyone this browser has not seen.
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
  const addMember = useChatStore((state) => state.addMember);

  const [members, setMembers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyUserId, setBusyUserId] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [leaving, setLeaving] = useState(false);

  const loadMembers = useCallback(async () => {
    setLoading(true);
    try {
      setMembers(await fetchMembers(conversationId));
      setError(null);
    } catch (err) {
      setError(describeApiError(err, "Could not load the member list."));
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  // Mirrors MembershipService.can_add_member on the server. Hiding the control
  // is a courtesy, not the control itself — the endpoint enforces it.
  const myRole = (members ?? []).find((m) => m.user_id === currentUser?.id)?.role;
  const canAddMembers = myRole === "owner" || myRole === "admin";

  async function withBusy(userId, action, successMessage) {
    setBusyUserId(userId);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(successMessage);
      // Re-read rather than patching locally: a role change can cascade (the
      // last-owner rule), and the server is the only thing that knows the
      // resulting state.
      await loadMembers();
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
        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="info">{notice}</Alert> : null}

        {/* Only groups accept new members: a private conversation is exactly
            two people, and anyone can join the public room themselves. The
            backend rejects both with 400 — this just avoids offering it. */}
        {conversation?.type === "group" && canAddMembers ? (
          <div className="space-y-2 rounded-lg border border-edge bg-surface p-2.5">
            <p className="text-xs font-medium text-slate-300">Add someone</p>
            <UserPicker
              placeholder="Search people…"
              excludeIds={(members ?? []).map((m) => m.user_id)}
              onSelect={(user) =>
                withBusy(
                  user.id,
                  () => addMember(conversationId, user.id),
                  `${user.display_name || user.username} added.`,
                )
              }
            />
          </div>
        ) : null}

        {loading && members === null ? (
          <div className="flex justify-center py-6">
            <Spinner className="h-5 w-5" />
          </div>
        ) : null}

        <ul className="space-y-2">
          {(members ?? []).map((member) => {
            const isSelf = member.user_id === currentUser?.id;
            const busy = busyUserId === member.user_id;
            // The member row carries a user_id, not a profile. Anyone this
            // browser has seen (search results, the conversation peer) resolves
            // to a name; anyone else degrades to a short id.
            const profile = isSelf ? currentUser : userCache[member.user_id];
            const label =
              profile?.display_name || profile?.username || shortId(member.user_id);

            return (
              <li
                key={member.id}
                className="rounded-lg border border-edge bg-surface p-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <Avatar user={profile} size={30} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-slate-100">
                      {label}
                      {isSelf ? (
                        <span className="ml-1 text-xs text-slate-500">(you)</span>
                      ) : null}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {profile?.username ? `@${profile.username} · ` : ""}
                      {member.role}
                    </p>
                  </div>
                  {busy ? <Spinner /> : null}
                </div>

                {!isSelf ? (
                  <div className="mt-2 flex items-center gap-2">
                    <select
                      value={member.role}
                      disabled={busy}
                      onChange={(event) => {
                        const role = event.target.value;
                        if (!role || role === member.role) return;
                        withBusy(
                          member.user_id,
                          () => changeMemberRole(conversationId, member.user_id, role),
                          `Role updated to ${role}.`,
                        );
                      }}
                      className="flex-1 rounded-md border border-edge bg-surface-sunken px-2 py-1 text-xs text-slate-200 focus:border-accent focus:outline-none"
                      aria-label={`Change role for ${label}`}
                    >
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
                          member.user_id,
                          () => removeMember(conversationId, member.user_id),
                          `${label} removed.`,
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

        {!loading && members?.length === 0 ? (
          <p className="text-xs text-slate-500">No active members.</p>
        ) : null}
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
