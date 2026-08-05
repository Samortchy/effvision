import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Avatar, Button, EmptyState } from "../../components/ui";
import MembersPanel from "./MembersPanel";
import MessageComposer from "./MessageComposer";
import MessageList from "./MessageList";
import MessageSearch from "./MessageSearch";
import TypingIndicator from "./TypingIndicator";
import { useConversationSocket } from "./useConversationSocket";
import { conversationTitle } from "../../lib/formatters";
import { useChatStore } from "../../stores/chatStore";

const CONNECTION_LABEL = {
  connecting: { text: "Connecting…", className: "bg-amber-400" },
  open: { text: "Live", className: "bg-emerald-400" },
  closed: { text: "Reconnecting…", className: "bg-amber-400" },
  error: { text: "Reconnecting…", className: "bg-red-400" },
  forbidden: { text: "No access", className: "bg-red-400" },
  idle: { text: "Offline", className: "bg-slate-500" },
};

export default function ChatPanel() {
  const { conversationId } = useParams();
  const conversation = useChatStore((state) =>
    state.conversations.find((c) => c.id === conversationId),
  );
  const thread = useChatStore((state) => state.threads[conversationId]);
  const setActiveConversation = useChatStore((state) => state.setActiveConversation);

  // Panel visibility is component-local — no reason for a store.
  const [showMembers, setShowMembers] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  const { connection, typingUserIds, notifyTyping, notifyStoppedTyping } =
    useConversationSocket(conversationId);

  useEffect(() => {
    if (conversationId) setActiveConversation(conversationId);
  }, [conversationId, setActiveConversation]);

  if (!conversationId) {
    return <EmptyState title="No conversation selected" />;
  }

  const notMember = thread?.error?.response?.status === 403;
  const status = CONNECTION_LABEL[connection] ?? CONNECTION_LABEL.idle;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b border-edge px-4 py-3">
        <Avatar user={conversation?.peer} size={34} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold text-white">
            {/* Deep-linking to a conversation this browser has not loaded yet
                is possible; the sidebar list is refreshed from the server on
                mount, so the title fills in once that lands. */}
            {conversation
              ? conversationTitle(conversation)
              : `Conversation ${conversationId.slice(0, 8)}…`}
          </h1>
          <p className="flex items-center gap-1.5 truncate text-xs text-slate-500">
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${status.className}`}
              aria-hidden="true"
            />
            <span>{status.text}</span>
            <span aria-hidden="true">·</span>
            <span className="truncate">
              {conversation?.peer
                ? `@${conversation.peer.username}`
                : conversation?.type ?? "loading…"}
            </span>
          </p>
        </div>

        <Button variant="ghost" onClick={() => setShowSearch((v) => !v)}>
          Search
        </Button>
        <Button variant="ghost" onClick={() => setShowMembers((v) => !v)}>
          Members
        </Button>
      </header>

      {showSearch ? <MessageSearch conversationId={conversationId} /> : null}

      {notMember ? (
        <EmptyState title="You are not a member of this conversation">
          The server rejected the history request with a 403.
        </EmptyState>
      ) : (
        <>
          <div className="flex min-h-0 flex-1">
            <MessageList conversationId={conversationId} />
            {showMembers ? (
              <MembersPanel
                conversationId={conversationId}
                onClose={() => setShowMembers(false)}
              />
            ) : null}
          </div>
          <TypingIndicator userIds={typingUserIds} />
          <MessageComposer
            conversationId={conversationId}
            onTyping={notifyTyping}
            onSent={notifyStoppedTyping}
          />
        </>
      )}
    </div>
  );
}
