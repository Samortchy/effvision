from __future__ import annotations
from collections.abc import Sequence
from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.notification import Notification, NotificationType
from domain.repositories.notification_repository import NotificationRepository
from infrastructure.database.models.notification import Notification as NotificationORM


class SQLAlchemyNotificationRepository(NotificationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self.session.execute(
            select(NotificationORM).where(NotificationORM.id == notification_id)
        )
        orm_notification = result.scalar_one_or_none()
        return self._to_domain(orm_notification) if orm_notification else None

    async def get_new_since(self, user_id: uuid.UUID, since: datetime | None) -> list[Notification]:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.user_id == user_id)
            .order_by(NotificationORM.created_at.asc())
        )
        if since is not None:
            stmt = stmt.where(NotificationORM.created_at >= since)

        result = await self.session.execute(stmt)
        return [self._to_domain(n) for n in result.scalars().all()]

    async def create_many(
        self, user_ids: Sequence[uuid.UUID], type: NotificationType, payload: dict[str, Any]
    ) -> list[Notification]:
        if not user_ids:
            return []

        # RETURNING rather than add_all(): id and created_at are both server-side
        # defaults, and a bare flush() would leave created_at expired — touching it
        # afterwards triggers a lazy refresh, which raises MissingGreenlet on an
        # async session.
        stmt = insert(NotificationORM).returning(NotificationORM)
        result = await self.session.execute(
            stmt,
            [{"user_id": user_id, "type": type, "payload": payload} for user_id in user_ids],
        )
        return [self._to_domain(n) for n in result.scalars().all()]

    async def mark_as_read(self, notification_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(NotificationORM).where(NotificationORM.id == notification_id)
        )
        orm_notification = result.scalar_one_or_none()
        if orm_notification:
            orm_notification.is_read = True
            await self.session.flush()

    @staticmethod
    def _to_domain(orm_notification: NotificationORM) -> Notification:
        return Notification(
            id=orm_notification.id,
            user_id=orm_notification.user_id,
            type=orm_notification.type,
            payload=orm_notification.payload,
            is_read=orm_notification.is_read,
            created_at=orm_notification.created_at,
        )
