import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Avatar, Button, EmptyState } from "../../components/ui";
import MembersPanel from "./MembersPanel";
import MessageComposer from "./MessageComposer";
import MessageList from "./MessageList";
import MessageSearch from "./MessageSearch";
import { conversationTitle } from "../../lib/formatters";
import { useChatStore } from "../../stores/chatStore";

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

  useEffect(() => {
    if (conversationId) setActiveConversation(conversationId);
  }, [conversationId, setActiveConversation]);

  if (!conversationId) {
    return <EmptyState title="No conversation selected" />;
  }

  const notMember = thread?.error?.response?.status === 403;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center gap-3 border-b border-edge px-4 py-3">
        <Avatar user={conversation?.peer} size={34} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold text-white">
            {/* Deep-linking to a conversation this browser has never seen is
                possible, and there is no endpoint to look one up by id. */}
            {conversation
              ? conversationTitle(conversation)
              : `Conversation ${conversationId.slice(0, 8)}…`}
          </h1>
          <p className="truncate text-xs text-slate-500">
            {conversation?.peer
              ? `@${conversation.peer.username}`
              : conversation?.type ?? "loading…"}
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
          <MessageComposer conversationId={conversationId} />
        </>
      )}
    </div>
  );
}
