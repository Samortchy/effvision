from __future__ import annotations
from datetime import datetime, timezone
import uuid

from domain.exceptions import MessageNotFoundError, NotMessageOwnerError
from domain.repositories.message_repository import MessageRepository


class DeleteMessageUseCase:
    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    async def execute(self, message_id: uuid.UUID, requesting_user_id: uuid.UUID) -> None:
        message = await self.message_repo.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError("Message not found")

        if message.sender_id != requesting_user_id:
            raise NotMessageOwnerError("You can only delete your own messages")

        await self.message_repo.delete_message(message_id, datetime.now(timezone.utc))