import { NavLink, useNavigate } from "react-router-dom";

import { Avatar, Button } from "./ui";
import UserSearch from "../features/users/UserSearch";
import NotificationBell from "../features/notifications/NotificationBell";
import { conversationTitle } from "../lib/formatters";
import { useAuthStore } from "../stores/authStore";
import { useChatStore } from "../stores/chatStore";

export default function Sidebar() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const conversations = useChatStore((state) => state.conversations);
  const resetChat = useChatStore((state) => state.reset);

  async function handleLogout() {
    await logout();
    resetChat();
    navigate("/login", { replace: true });
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

      <div className="border-b border-edge p-3">
        <UserSearch />
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto p-2">
        <h2 className="px-2 pb-2 pt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Conversations
        </h2>

        {conversations.length === 0 ? (
          <p className="px-2 text-sm text-slate-500">
            Nothing here yet. Search for someone above to start talking.
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

        {/* The list is local-only; say so rather than letting it look broken. */}
        <p className="mt-4 rounded-lg border border-edge/60 bg-surface/40 px-2 py-2 text-[11px] leading-relaxed text-slate-500">
          This list is stored in your browser. The backend has no
          “list my conversations” endpoint yet, so conversations started by
          other people appear only once they notify you.
        </p>
      </nav>

      <div className="border-t border-edge p-3">
        <Button variant="ghost" className="w-full" onClick={handleLogout}>
          Sign out
        </Button>
      </div>
    </aside>
  );
}
