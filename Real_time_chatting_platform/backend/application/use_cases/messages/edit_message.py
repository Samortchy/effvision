from datetime import datetime, timezone
from domain.repositories.message_repository import MessageRepository
from application.dto.message_dto import EditMessageRequest, MessageResponse
import structlog

logger = structlog.get_logger()

class MessageNotFoundError(Exception):
    def __init__(self, message_id):
        self.message_id = message_id
        super().__init__(f"message with message ID: {message_id} isn't found")

class NotMessageOwnerError(Exception):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(f"user: {user_id} isn't the message owner")

class EditMessageUseCase:
    def __init__(self, message_repo: MessageRepository):
        self._repo = message_repo

    async def execute(self, message_id, requester_id, data: EditMessageRequest) -> MessageResponse:
        message = await self._repo.get_by_id(message_id)
        if not message:
            raise MessageNotFoundError(message_id)

        if message.sender_id != requester_id:
            raise NotMessageOwnerError(requester_id)

        message.content = data.content
        message.is_edited = True
        message.edited_at = datetime.now(timezone.utc)

        updated = await self._repo.update(message)

        logger.info("message_edited", message_id=str(updated.id), sender_id=str(requester_id))

        return MessageResponse(
            id=updated.id, conversation_id=updated.conversation_id, sender_id=updated.sender_id,
            content=updated.content, is_edited=updated.is_edited,
            edited_at=updated.edited_at, created_at=updated.created_at,
        )