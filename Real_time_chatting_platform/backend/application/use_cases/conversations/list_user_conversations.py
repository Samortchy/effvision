from __future__ import annotations
from dataclasses import dataclass
import uuid

from domain.entities.conversation import Conversation
from domain.entities.user import User
from domain.repositories.conversation_repository import ConversationRepository


@dataclass(frozen=True)
class ConversationWithPeer:
    """A conversation plus, for private ones, who the caller is talking to.

    The peer is part of the *answer* rather than something the client is
    expected to remember. A private conversation carries no server-side name, so
    without this there is nothing to render as a title — which is exactly what
    used to happen after a logout, or on a second device: the sidebar showed a
    truncated conversation id.
    """

    conversation: Conversation
    peer: User | None


class ListUserConversationsUseCase:
    """Every conversation the caller is currently in.

    No authorization check beyond "you are the caller": the user id comes from
    the verified access token, not from the request, so there is no way to ask
    for somebody else's list.
    """

    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    async def execute(self, user_id: uuid.UUID) -> list[ConversationWithPeer]:
        conversations = await self.conversation_repo.list_for_user(user_id)

        # Two queries total, not one per conversation.
        private_ids = [c.id for c in conversations if c.type == "private"]
        peers = await self.conversation_repo.list_private_peers(private_ids, user_id)

        return [
            ConversationWithPeer(conversation=c, peer=peers.get(c.id))
            for c in conversations
        ]
