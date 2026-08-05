import { useCallback, useEffect, useRef, useState } from "react";

import { refreshAccessToken } from "../../lib/apiClient";
import { connectRealtime } from "../../lib/realtime";
import { useAccessToken } from "../../lib/useAccessToken";
import { useChatStore } from "../../stores/chatStore";

/** How long after the last keystroke we tell the server typing has stopped. */
const TYPING_IDLE_MS = 3000;

/**
 * One WebSocket per open conversation.
 *
 * Scoped to the conversation rather than the session because the route is
 * /ws/{conversation_id} — the server authorizes membership of one specific room
 * at handshake time. Navigating to another conversation tears this down and
 * opens the next one, which is what the effect's dependency list expresses.
 *
 * The token is a dependency too: it is baked into the URL, so a rotation has to
 * reopen the socket. useAccessToken re-renders on rotation, which re-runs this.
 */
export function useConversationSocket(conversationId) {
  const token = useAccessToken();
  const receiveMessage = useChatStore((state) => state.receiveMessage);

  const [connection, setConnection] = useState("idle");
  /** user_id -> timeout handle, for peers currently shown as typing. */
  const [typingUserIds, setTypingUserIds] = useState([]);

  const socketRef = useRef(null);
  const typingTimersRef = useRef(new Map());
  const sentTypingRef = useRef(false);
  const stopTypingTimerRef = useRef(null);

  useEffect(() => {
    if (!conversationId || !token) {
      setConnection("idle");
      return undefined;
    }

    const typingTimers = typingTimersRef.current;

    const socket = connectRealtime({
      token,
      conversationId,
      onStateChange: setConnection,
      onAuthExpired: () => {
        // Rotating the pair bumps the session version, which re-runs this
        // effect with a fresh token and opens a new socket.
        refreshAccessToken().catch(() => {
          /* unrecoverable — the 401 interceptor signs the user out */
        });
      },
      onMessage: (frame) => {
        switch (frame.type) {
          case "message":
            receiveMessage(frame.payload);
            break;

          case "typing_start": {
            const userId = frame.user_id;
            setTypingUserIds((ids) => (ids.includes(userId) ? ids : [...ids, userId]));
            // Self-expiring: a client that disconnects mid-type never sends
            // typing_stop, and without this the indicator would stick forever.
            clearTimeout(typingTimers.get(userId));
            typingTimers.set(
              userId,
              setTimeout(() => {
                setTypingUserIds((ids) => ids.filter((id) => id !== userId));
                typingTimers.delete(userId);
              }, TYPING_IDLE_MS + 1000),
            );
            break;
          }

          case "typing_stop": {
            const userId = frame.user_id;
            clearTimeout(typingTimers.get(userId));
            typingTimers.delete(userId);
            setTypingUserIds((ids) => ids.filter((id) => id !== userId));
            break;
          }

          default:
            /* "error" and anything unrecognised: nothing to render */
            break;
        }
      },
    });

    socketRef.current = socket;

    return () => {
      socket.close();
      socketRef.current = null;
      for (const timer of typingTimers.values()) clearTimeout(timer);
      typingTimers.clear();
      clearTimeout(stopTypingTimerRef.current);
      sentTypingRef.current = false;
      setTypingUserIds([]);
    };
  }, [conversationId, token, receiveMessage]);

  /**
   * Call on every keystroke. Sends typing_start once, then a single
   * typing_stop once the user goes quiet — rather than a frame per character.
   */
  const notifyTyping = useCallback(() => {
    if (!socketRef.current) return;

    if (!sentTypingRef.current) {
      socketRef.current.send({ type: "typing_start" });
      sentTypingRef.current = true;
    }

    clearTimeout(stopTypingTimerRef.current);
    stopTypingTimerRef.current = setTimeout(() => {
      socketRef.current?.send({ type: "typing_stop" });
      sentTypingRef.current = false;
    }, TYPING_IDLE_MS);
  }, []);

  /** Call right after a successful send: the message itself ends the typing state. */
  const notifyStoppedTyping = useCallback(() => {
    clearTimeout(stopTypingTimerRef.current);
    if (sentTypingRef.current) {
      socketRef.current?.send({ type: "typing_stop" });
      sentTypingRef.current = false;
    }
  }, []);

  return { connection, typingUserIds, notifyTyping, notifyStoppedTyping };
}
