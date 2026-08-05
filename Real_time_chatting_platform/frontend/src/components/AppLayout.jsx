import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import ToastHost from "../features/notifications/ToastHost";
import { useNotificationStream } from "../features/notifications/useNotificationStream";
import { useAuthStore } from "../stores/authStore";
import { useChatStore } from "../stores/chatStore";
import { useFriendStore } from "../stores/friendStore";

export default function AppLayout() {
  const isAuthenticated = useAuthStore((state) => state.status === "authenticated");
  const loadConversations = useChatStore((state) => state.loadConversations);
  const loadFriends = useFriendStore((state) => state.load);

  // One stream for the whole session, opened here so it survives navigation
  // between conversations.
  useNotificationStream(isAuthenticated);

  // The persisted list is only a first paint; the server is authoritative, and
  // it knows about conversations this browser has never seen.
  useEffect(() => {
    if (!isAuthenticated) return;
    loadConversations().catch(() => {
      /* the sidebar falls back to whatever was persisted */
    });
    // Loaded here rather than in the friends panel so the pending-request badge
    // is right before anyone opens it — a badge that only appears once you look
    // is not a badge.
    loadFriends().catch(() => {
      /* the badge stays at zero; the panel reports the error when opened */
    });
  }, [isAuthenticated, loadConversations, loadFriends]);

  return (
    <div className="flex h-full bg-surface-sunken">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col bg-surface">
        <Outlet />
      </main>
      <ToastHost />
    </div>
  );
}
