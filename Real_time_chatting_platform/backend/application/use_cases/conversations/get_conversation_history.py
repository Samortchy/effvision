from __future__ import annotations
from datetime import datetime
import uuid

from domain.entities.message import Message
from domain.exceptions import NotAConversationMemberError
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository


class GetConversationHistoryUseCase:
    def __init__(self, conversation_repo: ConversationRepository, message_repo: MessageRepository):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    async def execute(
        self, conversation_id: uuid.UUID, requesting_user_id: uuid.UUID, before: datetime | None, limit: int
    ) -> list[Message]:
        member = await self.conversation_repo.get_member(conversation_id, requesting_user_id)
        if member is None or member.left_at is not None:
            raise NotAConversationMemberError("You are not a member of this conversation")

        return await self.message_repo.get_conversation_history(conversation_id, before, limit)
