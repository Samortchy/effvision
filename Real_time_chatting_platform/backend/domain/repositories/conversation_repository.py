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
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

from domain.entities.conversation import Conversation
from domain.entities.conversation_member import ConversationMember, Role


class ConversationRepository(ABC):
    """Port for conversation + membership persistence."""

    @abstractmethod
    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        ...

    @abstractmethod
    async def get_private_conversation(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> Conversation | None:
        ...

    @abstractmethod
    async def create_private_conversation(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> Conversation:
        ...

    @abstractmethod
    async def add_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> ConversationMember:
        ...

    @abstractmethod
    async def get_member(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> ConversationMember | None:
        """Returns the membership row even if the user has left — callers that
        care about active membership must check `left_at`."""
        ...

    @abstractmethod
    async def list_members(self, conversation_id: uuid.UUID) -> list[ConversationMember]:
        """Active members only (`left_at IS NULL`)."""
        ...

    @abstractmethod
    async def update_member_role(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> None:
        """Raises MemberNotFoundError if there is no membership row."""
        ...

    @abstractmethod
    async def mark_member_left(self, conversation_id: uuid.UUID, user_id: uuid.UUID, left_at: datetime) -> None:
        """Used both for self-initiated 'leave' and admin-initiated 'remove' —
        the distinction (who/why) is an authorization concern handled by the
        use case layer, not the persistence layer.

        Raises MemberNotFoundError if there is no membership row."""
        ...