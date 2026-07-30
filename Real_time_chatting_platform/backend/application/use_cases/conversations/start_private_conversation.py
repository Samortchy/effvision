from __future__ import annotations
import uuid

from domain.entities.conversation import Conversation
from domain.exceptions import CannotMessageSelfError, UserNotFoundError
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.user_repository import UserRepository


class StartPrivateConversationUseCase:
    def __init__(self, conversation_repo: ConversationRepository, user_repo: UserRepository):
        self.conversation_repo = conversation_repo
        self.user_repo = user_repo

    async def execute(self, current_user_id: uuid.UUID, recipient_id: uuid.UUID) -> Conversation:
        if current_user_id == recipient_id:
            raise CannotMessageSelfError("Cannot start a conversation with yourself")

        # Without this the membership insert below fails on the users FK and
        # surfaces as a 500 instead of a 404.
        recipient = await self.user_repo.get_by_id(recipient_id)
        if recipient is None:
            raise UserNotFoundError("Recipient does not exist")

        existing = await self.conversation_repo.get_private_conversation(current_user_id, recipient_id)
        if existing is not None:
            return existing

        return await self.conversation_repo.create_private_conversation(current_user_id, recipient_id)
