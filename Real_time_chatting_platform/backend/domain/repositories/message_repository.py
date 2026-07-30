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
    async def delete_message(self, message_id: uuid.UUID, deleted_at: datetime) -> None:
        ...

    @abstractmethod
    async def search_messages(
        self, conversation_id: uuid.UUID, query: str, limit: int, offset: int
    ) -> list[Message]:
        ...
