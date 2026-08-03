from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.conversation import Conversation
from domain.entities.conversation_member import ConversationMember, Role
from domain.exceptions import MemberNotFoundError
from domain.repositories.conversation_repository import ConversationRepository
from infrastructure.database.models.conversation import (
    Conversation as ConversationORM,
    ConversationMember as ConversationMemberORM,
)


class SQLAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # Conversation methods
    # ------------------------------------------------------------------

    async def get_by_id(
        self, conversation_id: uuid.UUID
    ) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationORM).where(
                ConversationORM.id == conversation_id
            )
        )
        orm_conv = result.scalar_one_or_none()
        return self._conv_to_domain(orm_conv) if orm_conv else None

    async def get_public_conversation(self) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationORM).where(
                ConversationORM.type == "public"
            )
        )
        orm_conv = result.scalar_one_or_none()
        return self._conv_to_domain(orm_conv) if orm_conv else None

    async def get_private_conversation(
        self,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> Conversation | None:
        def _is_active_member(user_id: uuid.UUID):
            return exists().where(
                and_(
                    ConversationMemberORM.conversation_id == ConversationORM.id,
                    ConversationMemberORM.user_id == user_id,
                    ConversationMemberORM.left_at.is_(None),
                )
            )

        stmt = (
            select(ConversationORM)
            .where(ConversationORM.type == "private")
            .where(_is_active_member(user_a_id))
            .where(_is_active_member(user_b_id))
            .order_by(ConversationORM.created_at.asc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        orm_conv = result.scalars().first()
        return self._conv_to_domain(orm_conv) if orm_conv else None

    async def create(
        self,
        conversation: Conversation,
    ) -> Conversation:
        orm_conv = ConversationORM(
            type=conversation.type,
            name=conversation.name,
            description=conversation.description,
            avatar_url=getattr(conversation, "avatar_url", None),
            created_by=conversation.created_by,
        )

        self.session.add(orm_conv)
        await self.session.flush()

        return self._conv_to_domain(orm_conv)

    async def create_private_conversation(
        self,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> Conversation:
        orm_conv = ConversationORM(
            type="private",
            created_by=user_a_id,
        )

        self.session.add(orm_conv)
        await self.session.flush()

        self.session.add_all(
            [
                ConversationMemberORM(
                    conversation_id=orm_conv.id,
                    user_id=user_a_id,
                    role="member",
                ),
                ConversationMemberORM(
                    conversation_id=orm_conv.id,
                    user_id=user_b_id,
                    role="member",
                ),
            ]
        )

        await self.session.flush()

        return self._conv_to_domain(orm_conv)

    # ------------------------------------------------------------------
    # Member methods
    # ------------------------------------------------------------------

    async def add_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: Role = "member",
    ) -> ConversationMember:
        orm_member = ConversationMemberORM(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
        )

        self.session.add(orm_member)
        await self.session.flush()

        return self._member_to_domain(orm_member)

    async def get_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ConversationMember | None:
        result = await self.session.execute(
            select(ConversationMemberORM).where(
                ConversationMemberORM.conversation_id == conversation_id,
                ConversationMemberORM.user_id == user_id,
            )
        )

        orm_member = result.scalar_one_or_none()
        return self._member_to_domain(orm_member) if orm_member else None

    async def is_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        result = await self.session.execute(
            select(ConversationMemberORM).where(
                ConversationMemberORM.conversation_id == conversation_id,
                ConversationMemberORM.user_id == user_id,
                ConversationMemberORM.left_at.is_(None),
            )
        )

        return result.scalar_one_or_none() is not None

    async def list_members(
        self,
        conversation_id: uuid.UUID,
    ) -> list[ConversationMember]:
        result = await self.session.execute(
            select(ConversationMemberORM).where(
                ConversationMemberORM.conversation_id == conversation_id,
                ConversationMemberORM.left_at.is_(None),
            )
        )

        return [
            self._member_to_domain(member)
            for member in result.scalars().all()
        ]

    async def update_member_role(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: Role,
    ) -> None:
        orm_member = await self._get_member_orm(
            conversation_id,
            user_id,
        )
        orm_member.role = role
        await self.session.flush()

    async def mark_member_left(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        left_at: datetime,
    ) -> None:
        orm_member = await self._get_member_orm(
            conversation_id,
            user_id,
        )
        orm_member.left_at = left_at
        await self.session.flush()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_member_orm(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ConversationMemberORM:
        result = await self.session.execute(
            select(ConversationMemberORM).where(
                ConversationMemberORM.conversation_id == conversation_id,
                ConversationMemberORM.user_id == user_id,
            )
        )

        orm_member = result.scalar_one_or_none()

        if orm_member is None:
            raise MemberNotFoundError(
                "Target user is not a member of this conversation"
            )

        return orm_member

    @staticmethod
    def _conv_to_domain(
        orm_conv: ConversationORM,
    ) -> Conversation:
        return Conversation(
            id=orm_conv.id,
            type=orm_conv.type,
            name=orm_conv.name,
            description=orm_conv.description,
            avatar_url=orm_conv.avatar_url,
            created_by=orm_conv.created_by,
            created_at=orm_conv.created_at,
            updated_at=orm_conv.updated_at,
        )

    @staticmethod
    def _member_to_domain(
        orm_member: ConversationMemberORM,
    ) -> ConversationMember:
        return ConversationMember(
            id=orm_member.id,
            conversation_id=orm_member.conversation_id,
            user_id=orm_member.user_id,
            role=orm_member.role,
            joined_at=orm_member.joined_at,
            left_at=orm_member.left_at,
            muted=orm_member.muted,
            last_read_message_id=orm_member.last_read_message_id,
            last_read_at=orm_member.last_read_at,
        )

    async def list_member_ids(self, conversation_id) -> list:
        result = await self._session.execute(
            select(MemberModel.user_id).where(MemberModel.conversation_id == conversation_id)
        )
        return [row[0] for row in result.all()]