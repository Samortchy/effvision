from __future__ import annotations
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.system_announcement import SystemAnnouncement
from domain.repositories.system_announcement_repository import SystemAnnouncementRepository
from infrastructure.database.models.system import SystemAnnouncement as SystemAnnouncementORM


class SQLAlchemySystemAnnouncementRepository(SystemAnnouncementRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_new_since(
        self, since: datetime | None, limit: int = 100
    ) -> list[SystemAnnouncement]:
        stmt = (
            select(SystemAnnouncementORM)
            .order_by(SystemAnnouncementORM.created_at.asc())
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(SystemAnnouncementORM.created_at >= since)

        result = await self.session.execute(stmt)
        return [self._to_domain(a) for a in result.scalars().all()]

    @staticmethod
    def _to_domain(orm_announcement: SystemAnnouncementORM) -> SystemAnnouncement:
        return SystemAnnouncement(
            id=orm_announcement.id,
            title=orm_announcement.title,
            body=orm_announcement.body,
            created_by=orm_announcement.created_by,
            created_at=orm_announcement.created_at,
        )
