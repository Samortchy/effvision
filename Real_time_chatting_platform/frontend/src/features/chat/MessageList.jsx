import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

import { Avatar, Spinner } from "../../components/ui";
import { formatDay, formatTime, shortId } from "../../lib/formatters";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";

/** How close to the top counts as "asking for more". */
const SCROLL_THRESHOLD_PX = 120;

export default function MessageList({ conversationId }) {
  const currentUser = useAuthStore((state) => state.user);
  const thread = useChatStore((state) => state.threads[conversationId]);
  const userCache = useChatStore((state) => state.userCache);
  const loadOlderMessages = useChatStore((state) => state.loadOlderMessages);
  const deleteMessage = useChatStore((state) => state.deleteMessage);

  const scrollRef = useRef(null);
  /** scrollHeight captured before older messages are prepended. */
  const anchorRef = useRef(null);
  const didInitialScrollRef = useRef(false);

  const messages = thread?.messages ?? [];
  const hasMore = thread?.hasMore ?? false;
  const loadingOlder = thread?.loadingOlder ?? false;

  const handleScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element || loadingOlder || !hasMore) return;

    if (element.scrollTop <= SCROLL_THRESHOLD_PX) {
      // Remember the current height so the viewport can be pinned to the same
      // message once the older page lands.
      anchorRef.current = element.scrollHeight - element.scrollTop;
      loadOlderMessages(conversationId);
    }
  }, [conversationId, hasMore, loadingOlder, loadOlderMessages]);

  /**
   * Keep the reading position stable across a prepend.
   *
   * Prepending older messages grows scrollHeight above the viewport, which would
   * otherwise yank the user upward. Restoring scrollTop from the pre-prepend
   * offset keeps whatever they were reading exactly where it was. Layout effect,
   * not effect, so it happens before paint and never flickers.
   */
  useLayoutEffect(() => {
    const element = scrollRef.current;
    if (!element || anchorRef.current === null) return;
    element.scrollTop = element.scrollHeight - anchorRef.current;
    anchorRef.current = null;
  }, [messages.length]);

  // First page: jump to the newest message (the bottom).
  useEffect(() => {
    didInitialScrollRef.current = false;
  }, [conversationId]);

  useLayoutEffect(() => {
    const element = scrollRef.current;
    if (!element || didInitialScrollRef.current || messages.length === 0) return;
    element.scrollTop = element.scrollHeight;
    didInitialScrollRef.current = true;
  }, [messages.length]);

  if (thread?.loading && messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="min-h-0 flex-1 overflow-y-auto px-4 py-4"
    >
      {loadingOlder ? (
        <div className="flex justify-center pb-3">
          <Spinner />
        </div>
      ) : null}

      {!hasMore && messages.length > 0 ? (
        <p className="pb-4 text-center text-xs text-slate-600">
          Beginning of the conversation
        </p>
      ) : null}

      {messages.length === 0 && !thread?.loading ? (
        <p className="py-8 text-center text-sm text-slate-500">
          No messages yet.
        </p>
      ) : null}

      <ol className="space-y-1">
        {messages.map((message, index) => {
          const previous = messages[index - 1];
          const isMine = message.sender_id === currentUser?.id;
          const sender = isMine ? currentUser : userCache[message.sender_id];

          const showDayDivider =
            !previous ||
            new Date(previous.created_at).toDateString() !==
              new Date(message.created_at).toDateString();

          // Collapse the avatar/name on consecutive messages from one sender.
          const grouped =
            !showDayDivider &&
            previous?.sender_id === message.sender_id &&
            new Date(message.created_at) - new Date(previous.created_at) < 5 * 60 * 1000;

          return (
            <li key={message.id}>
              {showDayDivider ? (
                <div className="flex items-center gap-3 py-4">
                  <span className="h-px flex-1 bg-edge" />
                  <span className="text-xs text-slate-500">
                    {formatDay(message.created_at)}
                  </span>
                  <span className="h-px flex-1 bg-edge" />
                </div>
              ) : null}

              <div className="group flex items-start gap-2.5">
                <div className="w-9 shrink-0">
                  {grouped ? null : <Avatar user={sender} size={36} />}
                </div>

                <div className="min-w-0 flex-1">
                  {grouped ? null : (
                    <p className="flex items-baseline gap-2">
                      <span className="text-sm font-medium text-white">
                        {isMine
                          ? "You"
                          : sender?.display_name ||
                            sender?.username ||
                            // No bulk user lookup exists and MessageResponse
                            // carries no username, so unseen senders show an id.
                            shortId(message.sender_id)}
                      </span>
                      <span className="text-xs text-slate-500">
                        {formatTime(message.created_at)}
                      </span>
                      {message.is_edited ? (
                        <span className="text-xs text-slate-600">(edited)</span>
                      ) : null}
                    </p>
                  )}

                  <p className="whitespace-pre-wrap break-words text-sm text-slate-200">
                    {message.content}
                  </p>
                </div>

                {isMine ? (
                  <button
                    type="button"
                    onClick={() => deleteMessage(conversationId, message.id).catch(() => {})}
                    className="invisible shrink-0 rounded px-1.5 py-0.5 text-xs text-slate-500 transition hover:bg-surface-raised hover:text-red-300 group-hover:visible"
                    aria-label="Delete message"
                  >
                    Delete
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
