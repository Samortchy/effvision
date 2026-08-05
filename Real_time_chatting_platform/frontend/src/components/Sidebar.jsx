import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { Avatar, Button, Spinner } from "./ui";
import UserSearch from "../features/users/UserSearch";
import CreateGroupDialog from "../features/chat/CreateGroupDialog";
import FriendsPanel from "../features/friends/FriendsPanel";
import NotificationBell from "../features/notifications/NotificationBell";
import { describeApiError } from "../lib/apiClient";
import { conversationTitle } from "../lib/formatters";
import { useAuthStore } from "../stores/authStore";
import { useChatStore } from "../stores/chatStore";
import { selectIncomingCount, useFriendStore } from "../stores/friendStore";

export default function Sidebar() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const conversations = useChatStore((state) => state.conversations);
  const resetChat = useChatStore((state) => state.reset);
  const openPublicConversation = useChatStore((state) => state.openPublicConversation);

  const [joiningPublic, setJoiningPublic] = useState(false);
  const [publicError, setPublicError] = useState(null);
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [showFriends, setShowFriends] = useState(false);
  const incomingCount = useFriendStore(selectIncomingCount);
  const resetFriends = useFriendStore((state) => state.reset);

  // Already in the list once you have joined — the button below is only for
  // getting in the first time.
  const inPublicRoom = conversations.some((c) => c.type === "public");

  async function handleLogout() {
    await logout();
    resetChat();
    // Friends are per-account; leaving them in memory would show the previous
    // user's list to whoever signs in next on this browser.
    resetFriends();
    navigate("/login", { replace: true });
  }

  async function handleOpenPublic() {
    setJoiningPublic(true);
    setPublicError(null);
    try {
      const conversation = await openPublicConversation();
      navigate(`/c/${conversation.id}`);
    } catch (err) {
      setPublicError(describeApiError(err, "Could not open the public room."));
    } finally {
      setJoiningPublic(false);
    }
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-edge bg-surface-sunken">
      <div className="flex items-center justify-between gap-2 border-b border-edge px-4 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <Avatar user={user} size={32} />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">
              {user?.display_name || user?.username || "…"}
            </p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
          </div>
        </div>
        <NotificationBell />
      </div>

      <div className="space-y-2 border-b border-edge p-3">
        <UserSearch />

        <button
          type="button"
          onClick={() => setShowFriends(true)}
          className="flex w-full items-center gap-2 rounded-lg border border-edge px-2 py-2 text-left text-sm text-slate-300 transition hover:bg-surface-raised hover:text-white"
        >
          <span aria-hidden="true" className="text-slate-500">☺</span>
          <span className="flex-1">Friends</span>
          {incomingCount > 0 ? (
            <span
              className="rounded-full bg-accent px-1.5 text-[10px] font-semibold text-slate-950"
              aria-label={`${incomingCount} pending friend requests`}
            >
              {incomingCount > 9 ? "9+" : incomingCount}
            </span>
          ) : null}
        </button>

        <button
          type="button"
          onClick={() => setShowCreateGroup(true)}
          className="flex w-full items-center gap-2 rounded-lg border border-edge px-2 py-2 text-left text-sm text-slate-300 transition hover:bg-surface-raised hover:text-white"
        >
          <span aria-hidden="true" className="text-slate-500">+</span>
          <span className="flex-1">New group</span>
        </button>

        {!inPublicRoom ? (
          <button
            type="button"
            onClick={handleOpenPublic}
            disabled={joiningPublic}
            className="flex w-full items-center gap-2 rounded-lg border border-edge px-2 py-2 text-left text-sm text-slate-300 transition hover:bg-surface-raised hover:text-white disabled:opacity-60"
          >
            <span aria-hidden="true" className="text-slate-500">#</span>
            <span className="flex-1">Join the public room</span>
            {joiningPublic ? <Spinner /> : null}
          </button>
        ) : null}

        {publicError ? <p className="text-xs text-red-300">{publicError}</p> : null}
      </div>

      {showCreateGroup ? (
        <CreateGroupDialog onClose={() => setShowCreateGroup(false)} />
      ) : null}

      {showFriends ? <FriendsPanel onClose={() => setShowFriends(false)} /> : null}

      <nav className="min-h-0 flex-1 overflow-y-auto p-2">
        <h2 className="px-2 pb-2 pt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Conversations
        </h2>

        {conversations.length === 0 ? (
          <p className="px-2 text-sm text-slate-500">
            Nothing here yet. Join the public room above, or search for someone
            to start talking.
          </p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <NavLink
                  to={`/c/${conversation.id}`}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm transition ${
                      isActive
                        ? "bg-surface-raised text-white"
                        : "text-slate-300 hover:bg-surface-raised/60"
                    }`
                  }
                >
                  <Avatar user={conversation.peer} size={30} />
                  <span className="min-w-0 flex-1 truncate">
                    {conversationTitle(conversation)}
                  </span>
                  {conversation.type !== "private" ? (
                    <span className="rounded bg-surface px-1.5 py-0.5 text-[10px] uppercase text-slate-400">
                      {conversation.type}
                    </span>
                  ) : null}
                </NavLink>
              </li>
            ))}
          </ul>
        )}

      </nav>

      <div className="border-t border-edge p-3">
        <Button variant="ghost" className="w-full" onClick={handleLogout}>
          Sign out
        </Button>
      </div>
    </aside>
  );
}
