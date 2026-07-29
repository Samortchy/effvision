from __future__ import annotations
import uuid

from domain.exceptions import NotAConversationMemberError
from domain.repositories.broadcaster import Broadcaster
from domain.repositories.conversation_repository import ConversationRepository


class TypingIndicatorUseCase:
    def __init__(self, conversation_repo: ConversationRepository, broadcaster: Broadcaster):
        self.conversation_repo = conversation_repo
        self.broadcaster = broadcaster

    async def execute(self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_typing: bool) -> None:
        member = await self.conversation_repo.get_member(conversation_id, user_id)
        if member is None or member.left_at is not None:
            raise NotAConversationMemberError("You are not a member of this conversation")

        await self.broadcaster.broadcast_to_conversation(
            conversation_id,
            {
                "type": "typing_start" if is_typing else "typing_stop",
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
            },
        )