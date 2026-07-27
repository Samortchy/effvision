from __future__ import annotations
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models.user import User as UserORM
from datetime import datetime
from sqlalchemy import func

class SQLAlchemyUserRepository(UserRepository):

#search
    async def search_by_username(self, query: str, limit: int, offset: int) -> list[User]:
        stmt = (
            select(UserORM)
            .where(UserORM.username.op("%")(query))  # pg_trgm similarity operator, uses the GIN index
            .order_by(func.similarity(UserORM.username, query).desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        orm_users = result.scalars().all()
        return [self._to_domain(u) for u in orm_users]
#last seen
    async def update_last_seen(self, user_id: uuid.UUID, timestamp: datetime) -> None:
        result = await self.session.execute(select(UserORM).where(UserORM.id == user_id))
        orm_user = result.scalar_one_or_none()
        if orm_user:
            orm_user.last_seen_at = timestamp
            await self.session.flush()
    

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(UserORM).where(UserORM.id == user_id))
        orm_user = result.scalar_one_or_none()
        return self._to_domain(orm_user) if orm_user else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(UserORM).where(UserORM.email == email))
        orm_user = result.scalar_one_or_none()
        return self._to_domain(orm_user) if orm_user else None

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(UserORM).where(UserORM.username == username))
        orm_user = result.scalar_one_or_none()
        return self._to_domain(orm_user) if orm_user else None

    @staticmethod
    def _to_domain(orm_user: UserORM) -> User:
        """Converts the SQLAlchemy ORM object into a plain domain entity."""
        return User(
            id=orm_user.id,
            username=orm_user.username,
            email=orm_user.email,
            password_hash=orm_user.password_hash,
            display_name=orm_user.display_name,
            avatar_url=orm_user.avatar_url,
            bio=orm_user.bio,
            status=orm_user.status,
            last_seen_at=orm_user.last_seen_at,
            created_at=orm_user.created_at,
        )