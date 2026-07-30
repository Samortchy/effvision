from __future__ import annotations
from datetime import datetime
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.message import Message
from domain.repositories.message_repository import MessageRepository
from infrastructure.database.models.message import Message as MessageORM


class SQLAlchemyMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, message_id: uuid.UUID) -> Message | None:
        result = await self.session.execute(select(MessageORM).where(MessageORM.id == message_id))
        orm_message = result.scalar_one_or_none()
        return self._to_domain(orm_message) if orm_message else None

    async def create(self, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str) -> Message:
        orm_message = MessageORM(conversation_id=conversation_id, sender_id=sender_id, content=content)
        self.session.add(orm_message)
        await self.session.flush()
        return self._to_domain(orm_message)

    async def delete_message(self, message_id: uuid.UUID, deleted_at: datetime) -> None:
        # Soft delete: the row stays for audit/history, but every read path
        # filters on is_deleted, so it stops being visible to clients.
        result = await self.session.execute(select(MessageORM).where(MessageORM.id == message_id))
        orm_message = result.scalar_one_or_none()
        if orm_message:
            orm_message.is_deleted = True
            orm_message.deleted_at = deleted_at
            await self.session.flush()

    async def search_messages(
        self, conversation_id: uuid.UUID, query: str, limit: int, offset: int
    ) -> list[Message]:
        stmt = (
            select(MessageORM)
            .where(
                MessageORM.conversation_id == conversation_id,
                MessageORM.is_deleted.is_(False),
                MessageORM.search_vector.op("@@")(func.plainto_tsquery("english", query)),
            )
            .order_by(MessageORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def get_conversation_history(
        self, conversation_id: uuid.UUID, before: datetime | None, limit: int
    ) -> list[Message]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
            # Soft-deleted messages must never leave the repository.
            .where(MessageORM.is_deleted.is_(False))
            .order_by(MessageORM.created_at.desc())
            .limit(limit)
        )

        if before is not None:
            stmt = stmt.where(MessageORM.created_at < before)

        result = await self.session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    @staticmethod
    def _to_domain(orm_message: MessageORM) -> Message:
        return Message(
            id=orm_message.id,
            conversation_id=orm_message.conversation_id,
            sender_id=orm_message.sender_id,
            content=orm_message.content,
            is_edited=orm_message.is_edited,
            edited_at=orm_message.edited_at,
            is_deleted=orm_message.is_deleted,
            deleted_at=orm_message.deleted_at,
            created_at=orm_message.created_at,
        )