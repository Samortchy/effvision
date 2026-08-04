from __future__ import annotations
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from domain.entities.conversation import Conversation
from domain.entities.conversation_member import ConversationMember, Role
from domain.exceptions import MemberNotFoundError
from domain.repositories.conversation_repository import ConversationRepository
from infrastructure.database.models import Conversation as ConversationModel, ConversationMember as MemberModel


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
        result = await self.session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
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
