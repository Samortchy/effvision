from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

from domain.entities.message import Message


class MessageRepository(ABC):
    """Port for message persistence."""

    @abstractmethod
    async def get_by_id(self, message_id: uuid.UUID) -> Message | None:
        ...

    @abstractmethod
    async def create(self, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str) -> Message:
        ...

    @abstractmethod
    async def get_conversation_history(
        self, conversation_id: uuid.UUID, before: datetime | None, limit: int
    ) -> list[Message]:
        ...

    @abstractmethod
    async def update_content(
        self, message_id: uuid.UUID, content: str, edited_at: datetime
    ) -> Message:
        """Rewrite a message's body and stamp it as edited.

        Takes the id rather than a Message entity on purpose. Entities returned
        by this repository are plain dataclasses, detached from the ORM identity
        map — mutating one and handing it back would write nothing. Passing the
        id forces the implementation to load the row it actually intends to
        change.

        Raises MessageNotFoundError if there is no such message.
        """
        ...

    @abstractmethod
    async def delete_message(self, message_id: uuid.UUID, deleted_at: datetime) -> None:
        ...

    @abstractmethod
    async def search_messages(
        self, conversation_id: uuid.UUID, query: str, limit: int, offset: int
    ) -> list[Message]:
        ...
