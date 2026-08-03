import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import ToastHost from "../features/notifications/ToastHost";
import { useNotificationStream } from "../features/notifications/useNotificationStream";
import { useAuthStore } from "../stores/authStore";

export default function AppLayout() {
  const isAuthenticated = useAuthStore((state) => state.status === "authenticated");

  // One stream for the whole session, opened here so it survives navigation
  // between conversations.
  useNotificationStream(isAuthenticated);

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
