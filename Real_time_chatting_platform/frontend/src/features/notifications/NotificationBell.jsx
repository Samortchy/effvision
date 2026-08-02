import { useEffect, useRef, useState } from "react";

import { Button } from "../../components/ui";
import { formatRelative } from "../../lib/formatters";
import {
  notificationKey,
  selectUnreadCount,
  useNotificationStore,
} from "../../stores/notificationStore";

const CONNECTION_LABEL = {
  idle: { text: "Offline", className: "bg-slate-500" },
  connecting: { text: "Connecting…", className: "bg-amber-400" },
  open: { text: "Live", className: "bg-emerald-400" },
  error: { text: "Reconnecting…", className: "bg-red-400" },
};

/** Human-readable line for a streamed event. */
function describeEvent(event) {
  if (event.event_category === "system_announcement") {
    return { title: event.title, body: event.body };
  }

  const payload = event.payload ?? {};
  switch (event.type) {
    case "new_message":
      return {
        title: payload.sender_username
          ? `New message from ${payload.sender_username}`
          : "New message",
        body: payload.preview ?? payload.content ?? "",
      };
    case "friend_request":
      return { title: "Friend request", body: payload.username ?? "" };
    case "background_task":
      return { title: "Background task", body: payload.status ?? "" };
    default:
      return { title: event.type, body: "" };
  }
}

export default function NotificationBell() {
  const events = useNotificationStore((state) => state.events);
  const unreadCount = useNotificationStore(selectUnreadCount);
  const readKeys = useNotificationStore((state) => state.readKeys);
  const connection = useNotificationStore((state) => state.connection);
  const markRead = useNotificationStore((state) => state.markRead);
  const markAllRead = useNotificationStore((state) => state.markAllRead);

  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  // Close on an outside click — ordinary popover behaviour, local state.
  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event) {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const status = CONNECTION_LABEL[connection] ?? CONNECTION_LABEL.idle;

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifications (${unreadCount} unread)`}
        aria-expanded={open}
        className="relative rounded-lg p-2 text-slate-300 transition hover:bg-surface-raised hover:text-white"
      >
        <span aria-hidden="true">🔔</span>
        {unreadCount > 0 ? (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-slate-950">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-xl border border-edge bg-surface shadow-xl">
          <div className="flex items-center justify-between border-b border-edge px-3 py-2">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${status.className}`} />
              <span className="text-xs text-slate-400">{status.text}</span>
            </div>
            {unreadCount > 0 ? (
              <Button variant="ghost" className="px-2 py-1 text-xs" onClick={markAllRead}>
                Mark all read
              </Button>
            ) : null}
          </div>

          <ul className="max-h-96 overflow-y-auto">
            {events.length === 0 ? (
              <li className="px-3 py-6 text-center text-sm text-slate-500">
                Nothing yet.
              </li>
            ) : (
              events.map((event) => {
                const key = notificationKey(event);
                const isRead = readKeys.includes(key);
                const { title, body } = describeEvent(event);

                return (
                  <li key={key}>
                    <button
                      type="button"
                      onClick={() => markRead(event)}
                      className={`flex w-full flex-col items-start gap-0.5 border-b border-edge/50 px-3 py-2.5 text-left transition hover:bg-surface-raised ${
                        isRead ? "opacity-60" : ""
                      }`}
                    >
                      <span className="flex w-full items-center gap-2">
                        {!isRead ? (
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                        ) : null}
                        <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-100">
                          {title}
                        </span>
                        <span className="shrink-0 text-xs text-slate-500">
                          {formatRelative(event.created_at)}
                        </span>
                      </span>
                      {body ? (
                        <span className="line-clamp-2 text-xs text-slate-400">{body}</span>
                      ) : null}
                      {event.event_category === "system_announcement" ? (
                        <span className="text-[10px] uppercase tracking-wide text-slate-600">
                          Announcement
                        </span>
                      ) : null}
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export { describeEvent };
