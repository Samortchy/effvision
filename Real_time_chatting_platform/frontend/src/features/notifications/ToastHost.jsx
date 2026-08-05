import { useEffect, useRef } from "react";

import { describeEvent } from "./NotificationBell";
import { notificationKey, useNotificationStore } from "../../stores/notificationStore";

const TOAST_MS = 6000;

function Toast({ event, onDismiss }) {
  // onDismiss is a fresh closure on every parent render, so depending on it
  // directly restarted this timer whenever *any* notification arrived — during a
  // burst, earlier toasts never dismissed at all. The ref keeps the latest
  // callback reachable while leaving the effect's dependencies empty, so the
  // countdown starts once per toast and runs to completion.
  const dismissRef = useRef(onDismiss);
  useEffect(() => {
    dismissRef.current = onDismiss;
  }, [onDismiss]);

  useEffect(() => {
    const timer = setTimeout(() => dismissRef.current(), TOAST_MS);
    return () => clearTimeout(timer);
  }, []);

  const { title, body } = describeEvent(event);
  const isAnnouncement = event.event_category === "system_announcement";

  return (
    <div
      role="status"
      className={`pointer-events-auto w-80 rounded-xl border px-3.5 py-3 shadow-xl backdrop-blur ${
        isAnnouncement
          ? "border-accent/40 bg-accent/10"
          : "border-edge bg-surface-raised/95"
      }`}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-white">{title}</p>
          {body ? <p className="mt-0.5 line-clamp-3 text-xs text-slate-300">{body}</p> : null}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss notification"
          className="shrink-0 rounded px-1 text-slate-400 transition hover:text-white"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export default function ToastHost() {
  const toasts = useNotificationStore((state) => state.toasts);
  const dismissToast = useNotificationStore((state) => state.dismissToast);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-2">
      {toasts.slice(-4).map((event) => (
        <Toast
          key={notificationKey(event)}
          event={event}
          onDismiss={() => dismissToast(event)}
        />
      ))}
    </div>
  );
}
