import { create } from "zustand";

import apiClient from "../lib/apiClient";

/** Stable key across the two event families, whose ids come from different tables. */
const keyOf = (event) => `${event.event_category}:${event.id}`;

export const useNotificationStore = create((set, get) => ({
  /** Newest first. */
  events: [],
  /** Keys of events the user has seen/acknowledged locally. */
  readKeys: [],
  /** Events currently shown as toasts. */
  toasts: [],
  /** "idle" | "connecting" | "open" | "error" */
  connection: "idle",

  setConnection: (connection) => set({ connection }),

  /**
   * Fold in one streamed event.
   *
   * Deduplicated because the stream can legitimately replay: on reconnect the
   * browser sends Last-Event-ID and the server resumes from that timestamp
   * (api/routes/notifications.py::_parse_last_event_id), which can re-deliver
   * an event that shares a created_at with the cursor.
   */
  pushEvent: (event) => {
    const key = keyOf(event);
    if (get().events.some((existing) => keyOf(existing) === key)) return;

    set((state) => ({
      events: [event, ...state.events].slice(0, 200),
      toasts: [...state.toasts, event],
    }));
  },

  dismissToast: (event) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => keyOf(t) !== keyOf(event)),
    })),

  /**
   * Mark a notification read.
   *
   * Only real notifications can be marked: PATCH /notifications/{id}/read looks
   * the id up in the notifications table, and a system announcement's id comes
   * from a different table entirely, so sending one would 404. Announcements are
   * therefore acknowledged locally only.
   */
  markRead: async (event) => {
    const key = keyOf(event);
    set((state) => ({
      readKeys: state.readKeys.includes(key) ? state.readKeys : [...state.readKeys, key],
    }));

    if (event.event_category !== "notification") return;

    try {
      await apiClient.patch(`/notifications/${event.id}/read`);
    } catch {
      // Local read-state stands; the badge should not bounce back on a blip.
    }
  },

  markAllRead: async () => {
    const unread = get().events.filter((e) => !get().readKeys.includes(keyOf(e)));
    await Promise.all(unread.map((event) => get().markRead(event)));
  },

  reset: () => set({ events: [], readKeys: [], toasts: [], connection: "idle" }),
}));

/** Selector: number of unread events in the feed. */
export function selectUnreadCount(state) {
  return state.events.filter((event) => !state.readKeys.includes(keyOf(event))).length;
}

export function isEventRead(state, event) {
  return state.readKeys.includes(keyOf(event));
}

export { keyOf as notificationKey };
