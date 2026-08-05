from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
import uuid

from domain.entities.conversation import Conversation
from domain.entities.conversation_member import ConversationMember, Role
from domain.entities.user import User


class ConversationRepository(ABC):
    """Port for conversation + membership persistence."""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        ...

    @abstractmethod
    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        ...

    @abstractmethod
    async def get_public_conversation(self) -> Conversation | None:
        """The single global conversation, if it has been created yet.

        There is at most one — enforced by a partial unique index on
        (type) WHERE type = 'public', not by application code.
        """
        ...

    @abstractmethod
    async def create_public_conversation(self, name: str) -> Conversation:
        """Called once, from application startup. Racing callers lose on the
        partial unique index rather than creating a second global room."""
        ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID) -> list[Conversation]:
        """Every conversation the user is currently an active member of.

        Newest activity first. This is what lets a client rebuild its sidebar on
        a fresh device — without it the conversation list can only ever be local
        browser state, and a conversation someone else opens with you is
        invisible until they message you.
        """
        ...

    @abstractmethod
    async def list_private_peers(
        self, conversation_ids: Sequence[uuid.UUID], viewer_id: uuid.UUID
    ) -> dict[uuid.UUID, User]:
        """conversation_id -> the *other* participant, for private conversations.

        Batched deliberately: the caller has a whole page of conversations and
        resolving each one's peer with its own query would be a textbook N+1 on
        the busiest screen in the app.

        Only private conversations appear in the result. Group and public rooms
        have no single "other person", and inlining their rosters here would
        make this unbounded.
        """
        ...

    @abstractmethod
    async def get_private_conversation(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> Conversation | None:
        ...

    @abstractmethod
    async def create_private_conversation(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> Conversation:
        ...

    @abstractmethod
    async def create_group_conversation(
        self, name: str, description: str | None, created_by: uuid.UUID
    ) -> Conversation:
        """Create an empty group. The caller adds members, starting with the
        creator as owner — a group with no owner cannot be administered."""
        ...

    @abstractmethod
    async def reinstate_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> ConversationMember:
        """Clear `left_at` on an existing membership row and reset the role.

        Needed because leaving is a soft delete. The row survives, and
        `uq_conversation_member (conversation_id, user_id)` means a second
        INSERT for the same pair violates the constraint — so someone who left
        can only be re-added by reviving their original row.

        Raises MemberNotFoundError if there is no row to reinstate.
        """
        ...

    @abstractmethod
    async def add_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role = "member"
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

    @abstractmethod
    async def list_member_ids(self, conversation_id) -> list:
        ...