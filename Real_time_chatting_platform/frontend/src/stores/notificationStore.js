import { create } from "zustand";
import { persist } from "zustand/middleware";

import apiClient from "../lib/apiClient";

/** Stable key across the two event families, whose ids come from different tables. */
const keyOf = (event) => `${event.event_category}:${event.id}`;

/**
 * Cap on remembered read keys.
 *
 * The feed itself holds 200 events, so anything older than this can never be
 * on screen to look unread. Bounded because localStorage is not — an unbounded
 * append-only array would grow for the life of the browser profile.
 */
const MAX_READ_KEYS = 500;

export const useNotificationStore = create(
  persist(
    (set, get) => ({
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
          readKeys: state.readKeys.includes(key)
            ? state.readKeys
            : [...state.readKeys, key].slice(-MAX_READ_KEYS),
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
    }),
    {
      name: "effvision.notifications",
      /**
       * Read state only.
       *
       * It is the one thing here the server cannot tell us again. Announcements
       * are acknowledged purely locally, and even for real notifications the
       * stream replays from Last-Event-ID on reconnect — so without this, every
       * reload resurrected events the user had already dismissed as unread.
       *
       * Everything else is deliberately left in memory: `events` come back from
       * the replay, `toasts` would pop stale on boot, and `connection` describes
       * a socket that no longer exists.
       */
      partialize: (state) => ({ readKeys: state.readKeys }),
    },
  ),
);

/** Selector: number of unread events in the feed. */
export function selectUnreadCount(state) {
  return state.events.filter((event) => !state.readKeys.includes(keyOf(event))).length;
}

export function isEventRead(state, event) {
  return state.readKeys.includes(keyOf(event));
}

export { keyOf as notificationKey };
