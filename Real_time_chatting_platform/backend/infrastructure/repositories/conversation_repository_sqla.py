from __future__ import annotations
from collections.abc import Sequence
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from domain.entities.conversation import Conversation
from domain.entities.conversation_member import ConversationMember, Role
from domain.entities.user import User
from domain.exceptions import MemberNotFoundError
from domain.repositories.conversation_repository import ConversationRepository
from infrastructure.database.models import (
    Conversation as ConversationModel,
    ConversationMember as MemberModel,
    User as UserORM,
)
from infrastructure.repositories.user_repository_sqla import SQLAlchemyUserRepository


class SQLAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, conversation: Conversation) -> Conversation:
        row = ConversationModel(
            type=conversation.type,
            name=conversation.name,
            description=conversation.description,
            avatar_url=conversation.avatar_url,
            created_by=conversation.created_by,
        )
        self.session.add(row)
        await self.session.flush()
        # created_at/updated_at are server defaults, and the entity requires
        # both — refresh so they come back populated rather than expired.
        await self.session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_public_conversation(self) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.type == "public")
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def create_public_conversation(self, name: str) -> Conversation:
        row = ConversationModel(type="public", name=name)
        try:
            # Savepoint: a second caller racing this insert loses on the partial
            # unique index, and without the nested scope that failure would
            # poison the whole surrounding transaction instead of just this
            # statement — leaving nothing to fall back to.
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
        except IntegrityError:
            existing = await self.get_public_conversation()
            if existing is None:
                raise
            return existing

        await self.session.refresh(row)
        return self._to_entity(row)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Conversation]:
        # Ordered by the conversation's own updated_at rather than by a
        # correlated "last message" subquery: updated_at is already indexed and
        # maintained by the set_updated_at() trigger, and this endpoint feeds a
        # sidebar, not an audit.
        result = await self.session.execute(
            select(ConversationModel)
            .join(MemberModel, MemberModel.conversation_id == ConversationModel.id)
            .where(
                MemberModel.user_id == user_id,
                MemberModel.left_at.is_(None),
            )
            .order_by(ConversationModel.updated_at.desc())
        )
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list_private_peers(
        self, conversation_ids: Sequence[uuid.UUID], viewer_id: uuid.UUID
    ) -> dict[uuid.UUID, User]:
        if not conversation_ids:
            return {}

        # One query for the whole page. The join to conversations is what keeps
        # this to private rooms only — without it a group's entire membership
        # would come back and the dict would silently keep whichever row landed
        # last.
        result = await self.session.execute(
            select(MemberModel.conversation_id, UserORM)
            .join(UserORM, UserORM.id == MemberModel.user_id)
            .join(ConversationModel, ConversationModel.id == MemberModel.conversation_id)
            .where(
                MemberModel.conversation_id.in_(conversation_ids),
                MemberModel.user_id != viewer_id,
                MemberModel.left_at.is_(None),
                ConversationModel.type == "private",
            )
        )
        return {
            conversation_id: SQLAlchemyUserRepository._to_domain(orm_user)
            for conversation_id, orm_user in result.all()
        }

    async def get_private_conversation(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ) -> Conversation | None:
        # Two independent joins onto the membership table: one row proves each
        # user is in the conversation. A private conversation cannot be left
        # (see LeaveGroupUseCase), so there is no left_at to filter here.
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
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def create_private_conversation(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ) -> Conversation:
        row = ConversationModel(type="private", created_by=user_a_id)
        self.session.add(row)
        await self.session.flush()

        # Neither party owns a 1:1 conversation — there is nothing to administer
        # and no one to remove, so both join as plain members.
        self.session.add_all(
            [
                MemberModel(conversation_id=row.id, user_id=user_a_id, role="member"),
                MemberModel(conversation_id=row.id, user_id=user_b_id, role="member"),
            ]
        )
        await self.session.flush()
        await self.session.refresh(row)
        return self._to_entity(row)

    async def create_group_conversation(
        self, name: str, description: str | None, created_by: uuid.UUID
    ) -> Conversation:
        row = ConversationModel(
            type="group",
            name=name,
            description=description,
            created_by=created_by,
        )
        self.session.add(row)
        await self.session.flush()
        # created_at/updated_at are server defaults and the entity requires
        # both — refresh so they come back populated rather than expired.
        await self.session.refresh(row)
        return self._to_entity(row)

    async def reinstate_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role = "member"
    ) -> ConversationMember:
        row = await self._load_member_row(conversation_id, user_id)
        row.left_at = None
        row.role = role
        await self.session.flush()
        return self._member_to_entity(row)

    async def add_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role = "member"
    ) -> ConversationMember:
        row = MemberModel(conversation_id=conversation_id, user_id=user_id, role=role)
        self.session.add(row)
        await self.session.flush()
        # id, joined_at and muted are all server defaults; the caller gets a
        # fully populated member back (JoinPublicConversationUseCase returns it).
        await self.session.refresh(row)
        return self._member_to_entity(row)

    async def get_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationMember | None:
        # Returns the row even when left_at is set — callers that require
        # *active* membership check left_at themselves.
        result = await self.session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        return self._member_to_entity(row) if row else None

    async def list_members(self, conversation_id: uuid.UUID) -> list[ConversationMember]:
        result = await self.session.execute(
            select(MemberModel)
            .where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.left_at.is_(None),
            )
            .order_by(MemberModel.joined_at.asc())
        )
        return [self._member_to_entity(row) for row in result.scalars().all()]

    async def list_member_ids(self, conversation_id) -> list:
        result = await self.session.execute(
            select(MemberModel.user_id).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.left_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def update_member_role(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: Role
    ) -> None:
        row = await self._load_member_row(conversation_id, user_id)
        row.role = role
        await self.session.flush()

    async def mark_member_left(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, left_at: datetime
    ) -> None:
        row = await self._load_member_row(conversation_id, user_id)
        row.left_at = left_at
        await self.session.flush()

    async def is_member(self, conversation_id, user_id) -> bool:
        """Active membership only — unlike get_member, which returns left rows.

        `left_at IS NULL` is the difference between "was ever in this room" and
        "is in it now". Without it a user who left, or whom an admin removed,
        keeps passing the WebSocket authorization check in
        api/websocket/chat_ws.py and goes on receiving the room's traffic.
        """
        result = await self.session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
                MemberModel.left_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def _load_member_row(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> MemberModel:
        """The ORM row itself, so mutations land in the session's identity map
        and are flushed. Raises MemberNotFoundError when there is no row, which
        is the contract both write paths declare."""
        result = await self.session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise MemberNotFoundError("No membership row for that user in this conversation")
        return row

    @staticmethod
    def _to_entity(row: ConversationModel) -> Conversation:
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
    def _member_to_entity(row: MemberModel) -> ConversationMember:
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
