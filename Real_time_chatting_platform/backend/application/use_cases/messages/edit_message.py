from __future__ import annotations
from datetime import datetime, timezone
import uuid

import structlog

from application.dto.message_dto import EditMessageRequest, MessageResponse
from domain.exceptions import MessageNotFoundError, NotMessageOwnerError
from domain.repositories.message_repository import MessageRepository

logger = structlog.get_logger()


class EditMessageUseCase:
    """Rewrite the body of a message the caller sent.

    Errors are the shared ones from domain.exceptions, not local look-alikes.
    Two classes with the same name in different modules do not compare equal, so
    a route that imports one and a use case that raises the other means the
    `except` clause silently never matches — which turned "you may only edit your
    own messages" from a 403 into a 500.
    """

    def __init__(self, message_repo: MessageRepository):
        self._repo = message_repo

    async def execute(
        self, message_id: uuid.UUID, requester_id: uuid.UUID, data: EditMessageRequest
    ) -> MessageResponse:
        message = await self._repo.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError("Message not found")

        if message.sender_id != requester_id:
            raise NotMessageOwnerError("You can only edit your own messages")

        # A deleted message has no body to rewrite. Without this check an edit
        # would resurrect the content of a message the sender already withdrew,
        # while every read path still filters it out — so the row would carry
        # text nobody can see and the edit would look like it silently failed.
        if message.is_deleted:
            raise MessageNotFoundError("Message not found")

        # The repository loads and mutates the ORM row itself. Assigning to the
        # `message` dataclass here would change nothing: it is detached from the
        # session, so flush() has no idea it exists.
        updated = await self._repo.update_content(
            message_id=message_id,
            content=data.content,
            edited_at=datetime.now(timezone.utc),
        )

        logger.info("message_edited", message_id=str(updated.id), sender_id=str(requester_id))

        return MessageResponse(
            id=updated.id,
            conversation_id=updated.conversation_id,
            sender_id=updated.sender_id,
            content=updated.content,
            is_edited=updated.is_edited,
            edited_at=updated.edited_at,
            created_at=updated.created_at,
        )
