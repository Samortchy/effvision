import { create } from "zustand";

import * as friendsApi from "../features/friends/api";
import { useChatStore } from "./chatStore";

/**
 * Friends and pending requests.
 *
 * Not persisted: unlike the conversation list this is cheap to fetch and
 * changes underneath you (someone can accept while you are away), so a stale
 * cached copy would be worse than a brief spinner.
 */
export const useFriendStore = create((set, get) => ({
  friends: [],
  incoming: [],
  outgoing: [],
  loading: false,
  error: null,

  /** One round trip per list; they are independent endpoints. */
  load: async () => {
    set({ loading: true, error: null });
    try {
      const [friends, incoming, outgoing] = await Promise.all([
        friendsApi.fetchFriends(),
        friendsApi.fetchFriendRequests("incoming"),
        friendsApi.fetchFriendRequests("outgoing"),
      ]);
      set({ friends, incoming, outgoing, loading: false });

      // Friends and requesters are exactly the people whose names we will need
      // beside messages later — messages carry only sender_id.
      useChatStore.getState().cacheUsers([
        ...friends,
        ...incoming.map((r) => r.user),
        ...outgoing.map((r) => r.user),
      ]);
    } catch (error) {
      set({ loading: false, error });
      throw error;
    }
  },

  sendRequest: async (userId) => {
    const request = await friendsApi.sendFriendRequest(userId);
    set((state) => ({ outgoing: [request, ...state.outgoing] }));
    return request;
  },

  /**
   * Accepting moves someone from `incoming` to `friends`, so both lists are
   * re-read rather than patched — the server is the only thing that knows
   * whether the friendship actually landed.
   */
  accept: async (requestId) => {
    await friendsApi.acceptFriendRequest(requestId);
    await get().load();
  },

  decline: async (requestId) => {
    await friendsApi.declineFriendRequest(requestId);
    set((state) => ({ incoming: state.incoming.filter((r) => r.id !== requestId) }));
  },

  remove: async (userId) => {
    await friendsApi.removeFriend(userId);
    set((state) => ({ friends: state.friends.filter((u) => u.id !== userId) }));
  },

  reset: () => set({ friends: [], incoming: [], outgoing: [], loading: false, error: null }),
}));

/** Selector: pending incoming requests, for the sidebar badge. */
export function selectIncomingCount(state) {
  return state.incoming.length;
}
