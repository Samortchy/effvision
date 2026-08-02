from __future__ import annotations
from datetime import datetime
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import aliased

from domain.entities.conversation import Conversation
from domain.entities.conversation_member import ConversationMember, Role
from domain.exceptions import MemberNotFoundError
from domain.repositories.conversation_repository import ConversationRepository
from infrastructure.database.models import (
    Conversation as ConversationModel,
    ConversationMember as MemberModel,
)

from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyConversationRepository(ConversationRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    # Writes flush rather than commit: get_db() owns the transaction and commits
    # once the request succeeds, so a use case that fails halfway through a
    # multi-step change (create conversation, then add members) rolls the whole
    # thing back instead of leaving a conversation with no members in it.

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        row = result.scalar_one_or_none()
        return self._to_conversation(row) if row else None

    async def get_public_conversation(self) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.type == "public")
        )
        row = result.scalar_one_or_none()
        return self._to_conversation(row) if row else None

    async def create_public_conversation(self, name: str) -> Conversation:
        row = ConversationModel(type="public", name=name)
        self.session.add(row)
        await self.session.flush()
        return self._to_conversation(row)

    async def get_private_conversation(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ) -> Conversation | None:
        """The private conversation both users belong to, or None.

        Self-joins the membership table once per user: a conversation only
        qualifies if it has a row for *both*, which a single WHERE user_id IN
        (a, b) could not express — that would match a conversation containing
        either one of them.
        """
        member_a = aliased(MemberModel)
        member_b = aliased(MemberModel)

        result = await self.session.execute(
            select(ConversationModel)
            .join(member_a, member_a.conversation_id == ConversationModel.id)
            .join(member_b, member_b.conversation_id == ConversationModel.id)
            .where(
                ConversationModel.type == "private",
                member_a.user_id == user_a_id,
                member_b.user_id == user_b_id,
            )
        )
        row = result.scalars().first()
        return self._to_conversation(row) if row else None

    async def create_private_conversation(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ) -> Conversation:
        row = ConversationModel(type="private", name=None, created_by=user_a_id)
        self.session.add(row)
        # Flush before the membership rows: they need the conversation's
        # server-generated id, and the FK would fail without the parent INSERT.
        await self.session.flush()

        # Both sides are plain members. Neither party owns a 1:1 conversation —
        # there is no one to administer and nobody can leave it.
        self.session.add_all(
            [
                MemberModel(conversation_id=row.id, user_id=user_a_id, role="member"),
                MemberModel(conversation_id=row.id, user_id=user_b_id, role="member"),
            ]
        )
        await self.session.flush()
        return self._to_conversation(row)

    async def add_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> ConversationMember:
        row = MemberModel(conversation_id=conversation_id, user_id=user_id, role=role)
        self.session.add(row)
        await self.session.flush()
        return self._to_member(row)

    async def get_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationMember | None:
        result = await self.session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        # Returned even when left_at is set — callers decide whether a former
        # member counts, and some (role checks on past messages) need the row.
        return self._to_member(row) if row else None

    async def list_members(self, conversation_id: uuid.UUID) -> list[ConversationMember]:
        result = await self.session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.left_at.is_(None),
            )
        )
        return [self._to_member(row) for row in result.scalars().all()]

    async def update_member_role(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> None:
        result = await self.session.execute(
            update(MemberModel)
            .where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
            )
            .values(role=role)
        )
        if result.rowcount == 0:
            raise MemberNotFoundError("That user is not a member of this conversation")

    async def mark_member_left(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, left_at: datetime
    ) -> None:
        result = await self.session.execute(
            update(MemberModel)
            .where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
                # Guards against a double-leave silently moving the timestamp;
                # the row stays stamped with when they *first* left.
                MemberModel.left_at.is_(None),
            )
            .values(left_at=left_at)
        )
        if result.rowcount == 0:
            raise MemberNotFoundError("That user is not an active member of this conversation")

    @staticmethod
    def _to_conversation(row: ConversationModel) -> Conversation:
        return Conversation(
            id=row.id,
            type=row.type,
            name=row.name,
            description=row.description,
            avatar_url=row.avatar_url,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_member(row: MemberModel) -> ConversationMember:
        return ConversationMember(
            id=row.id,
            conversation_id=row.conversation_id,
            user_id=row.user_id,
            role=row.role,
            joined_at=row.joined_at,
            left_at=row.left_at,
            muted=row.muted,
            last_read_message_id=row.last_read_message_id,
            last_read_at=row.last_read_at,
        )
