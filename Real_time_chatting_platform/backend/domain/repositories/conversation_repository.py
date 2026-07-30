from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.conversations import Conversation

class ConversationRepository:

    @abstractmethod
    async def get_public_conversation(self) -> Conversation | None:
        ...

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    async def add_member(self, conversation_id, user_id, role_str = "member") -> None:
        ...

    @abstractmethod
    async def is_member(self, conversation_id, user_id) -> bool:
        ...