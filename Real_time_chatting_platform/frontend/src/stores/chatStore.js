import { create } from "zustand";
import { persist } from "zustand/middleware";

import * as chatApi from "../features/chat/api";

/** Server caps `limit` at 100; 30 is a comfortable screenful with room to scroll. */
export const PAGE_SIZE = 30;

const emptyThread = {
  messages: [], // ascending (oldest first) — the API returns descending
  hasMore: true,
  loading: false,
  loadingOlder: false,
  error: null,
};

/**
 * Conversation + message state.
 *
 * ⚠️ The conversation list is local-only. The backend has no
 * "list my conversations" route (api/routes/conversations.py exposes just
 * /private, /{id}/messages, /leave and the two member routes), so the sidebar
 * can only show conversations this browser has seen. Consequences to be aware
 * of: a fresh device starts empty, and a conversation someone else opened with
 * you will not appear until a notification or a message reveals it. Persisting
 * to localStorage is what makes it survive a reload at all.
 */
export const useChatStore = create(
  persist(
    (set, get) => ({
      conversations: [],
      activeConversationId: null,
      threads: {},

      /**
       * id -> UserSummary. MessageResponse carries only `sender_id`, with no
       * username or avatar, and there is no bulk user-lookup endpoint — so the
       * only way to render a name next to a message is to remember users we
       * have already seen (search results, conversation peers).
       */
      userCache: {},

      cacheUsers: (users) =>
        set((state) => ({
          userCache: users.reduce(
            (acc, user) => ({ ...acc, [user.id]: user }),
            state.userCache,
          ),
        })),

      /** Start (or re-open) a 1:1 conversation and select it. */
      openPrivateConversation: async (peer) => {
        const conversation = await chatApi.startPrivateConversation(peer.id);

        set((state) => {
          const existing = state.conversations.find((c) => c.id === conversation.id);
          const entry = { ...conversation, peer };
          return {
            conversations: existing
              ? state.conversations.map((c) => (c.id === entry.id ? entry : c))
              : [entry, ...state.conversations],
            userCache: { ...state.userCache, [peer.id]: peer },
            activeConversationId: conversation.id,
          };
        });

        await get().loadInitialHistory(conversation.id);
        return conversation;
      },

      setActiveConversation: (conversationId) => {
        set({ activeConversationId: conversationId });
        const thread = get().threads[conversationId];
        // Only fetch the first time; afterwards the thread is already warm.
        if (!thread) get().loadInitialHistory(conversationId);
      },

      _patchThread: (conversationId, patch) =>
        set((state) => ({
          threads: {
            ...state.threads,
            [conversationId]: {
              ...emptyThread,
              ...state.threads[conversationId],
              ...patch,
            },
          },
        })),

      /** Newest page. Reversed into ascending order for rendering. */
      loadInitialHistory: async (conversationId) => {
        get()._patchThread(conversationId, { loading: true, error: null });
        try {
          const page = await chatApi.fetchMessageHistory(conversationId, {
            limit: PAGE_SIZE,
          });
          get()._patchThread(conversationId, {
            messages: [...page].reverse(),
            // A full page means there is probably more behind it. A short page
            // is a definitive end.
            hasMore: page.length === PAGE_SIZE,
            loading: false,
          });
        } catch (error) {
          get()._patchThread(conversationId, { loading: false, error });
        }
      },

      /**
       * Scroll-back page. The cursor is the oldest message we hold; `before` is
       * exclusive server-side so nothing is duplicated at the seam.
       */
      loadOlderMessages: async (conversationId) => {
        const thread = get().threads[conversationId];
        if (!thread || thread.loadingOlder || !thread.hasMore) return;
        if (thread.messages.length === 0) return get().loadInitialHistory(conversationId);

        get()._patchThread(conversationId, { loadingOlder: true });
        try {
          const page = await chatApi.fetchMessageHistory(conversationId, {
            before: thread.messages[0].created_at,
            limit: PAGE_SIZE,
          });

          const current = get().threads[conversationId];
          // Defensive: if two loads ever overlap, drop ids we already hold.
          const known = new Set(current.messages.map((m) => m.id));
          const older = [...page].reverse().filter((m) => !known.has(m.id));

          get()._patchThread(conversationId, {
            messages: [...older, ...current.messages],
            hasMore: page.length === PAGE_SIZE,
            loadingOlder: false,
          });
        } catch (error) {
          get()._patchThread(conversationId, { loadingOlder: false, error });
        }
      },

      /** Append a message that arrived in real time (or was sent by us). */
      receiveMessage: (message) => {
        const thread = get().threads[message.conversation_id];
        if (!thread) return;
        if (thread.messages.some((m) => m.id === message.id)) return;
        get()._patchThread(message.conversation_id, {
          messages: [...thread.messages, message],
        });
      },

      /** Soft delete. Only the sender may do this; anyone else gets a 403. */
      deleteMessage: async (conversationId, messageId) => {
        const thread = get().threads[conversationId];
        const previous = thread?.messages ?? [];

        // Optimistic: pull it out now, put it back if the server disagrees.
        get()._patchThread(conversationId, {
          messages: previous.filter((m) => m.id !== messageId),
        });

        try {
          await chatApi.deleteMessage(messageId);
        } catch (error) {
          get()._patchThread(conversationId, { messages: previous, error });
          throw error;
        }
      },

      /** ⚠️ PENDING BACKEND — see chat/api.js sendMessage. */
      sendMessage: async (conversationId, content) => {
        await chatApi.sendMessage(conversationId, content);
      },

      leaveConversation: async (conversationId) => {
        await chatApi.leaveConversation(conversationId);
        get().forgetConversation(conversationId);
      },

      changeMemberRole: async (conversationId, targetUserId, role) => {
        await chatApi.changeMemberRole(conversationId, targetUserId, role);
      },

      removeMember: async (conversationId, targetUserId) => {
        await chatApi.removeMember(conversationId, targetUserId);
      },

      /** Drop a conversation from the local list (after leaving, say). */
      forgetConversation: (conversationId) =>
        set((state) => {
          const { [conversationId]: _removed, ...threads } = state.threads;
          return {
            conversations: state.conversations.filter((c) => c.id !== conversationId),
            threads,
            activeConversationId:
              state.activeConversationId === conversationId
                ? null
                : state.activeConversationId,
          };
        }),

      reset: () =>
        set({
          conversations: [],
          activeConversationId: null,
          threads: {},
          userCache: {},
        }),
    }),
    {
      name: "effvision.chat",
      // Messages are deliberately not persisted — they are re-fetched from the
      // server, and stale ones would fight with the cursor logic. Only the
      // things the API cannot tell us are kept.
      partialize: (state) => ({
        conversations: state.conversations,
        userCache: state.userCache,
      }),
    },
  ),
);
