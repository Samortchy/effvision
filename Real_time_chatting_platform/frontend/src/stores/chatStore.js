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
 * The conversation list comes from GET /conversations and is refreshed by
 * loadConversations() on mount. It is still persisted to localStorage, but only
 * so the sidebar has something to paint before that request lands — the server
 * is the source of truth, and the persisted copy is overwritten as soon as it
 * answers.
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

      /**
       * Authoritative conversation list from GET /conversations.
       *
       * Replaces the locally-remembered list rather than merging into it: the
       * server knows about conversations this browser has never seen (someone
       * opened one with you), and it also knows about ones you have left. A
       * merge would keep the latter around forever.
       *
       * `peer` now comes from the server for private conversations, so a title
       * survives a logout and is correct on a device that has never seen the
       * other person. The locally-remembered one is only a fallback for the
       * moment between an optimistic openPrivateConversation and this landing.
       */
      loadConversations: async () => {
        const conversations = await chatApi.fetchMyConversations();
        set((state) => {
          const previousById = Object.fromEntries(
            state.conversations.map((c) => [c.id, c]),
          );
          // Peers are exactly the users we need names for later — messages
          // carry only sender_id, so seed the cache from them.
          const userCache = { ...state.userCache };
          for (const c of conversations) {
            if (c.peer) userCache[c.peer.id] = c.peer;
          }
          return {
            conversations: conversations.map((c) => ({
              ...c,
              peer: c.peer ?? previousById[c.id]?.peer,
            })),
            userCache,
          };
        });
        return conversations;
      },

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

      /** Create a group, refresh the list from the server, and select it. */
      createGroup: async ({ name, description, memberIds }) => {
        const conversation = await chatApi.createGroup({ name, description, memberIds });
        await get().loadConversations();
        set({ activeConversationId: conversation.id });
        await get().loadInitialHistory(conversation.id);
        return conversation;
      },

      addMember: async (conversationId, userId, role) =>
        chatApi.addMember(conversationId, userId, role),

      /**
       * Open the global public room, joining it first if necessary.
       *
       * Join-then-open rather than checking membership first: the endpoint is
       * the only thing that knows, and a 409 ("already a member") is a success
       * for this purpose — it means the postcondition we want already holds.
       * Treating it as an error would make the button fail for everyone who has
       * used it once.
       */
      openPublicConversation: async () => {
        const conversation = await chatApi.fetchPublicConversation();

        try {
          await chatApi.joinPublicConversation();
        } catch (error) {
          if (error?.response?.status !== 409) throw error;
        }

        await get().loadConversations();
        set({ activeConversationId: conversation.id });
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

      /**
       * Send, then fold the server's copy into the thread.
       *
       * The broadcast excludes the sender (otherwise our own message would
       * arrive twice — once as this response, once over the socket), so this is
       * the only place our client learns its own message id and created_at.
       * receiveMessage dedupes by id, so a racing socket frame is harmless.
       */
      sendMessage: async (conversationId, content) => {
        const message = await chatApi.sendMessage(conversationId, content);
        get().receiveMessage(message);
        return message;
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
