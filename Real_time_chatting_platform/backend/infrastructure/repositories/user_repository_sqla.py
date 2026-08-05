from __future__ import annotations
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.exceptions import UserAlreadyExistsError
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models.user import User as UserORM
from datetime import datetime
from sqlalchemy import func

class SQLAlchemyUserRepository(UserRepository):

    async def update(self, user: User) -> User:
        result = await self.session.execute(select(UserORM).where(UserORM.id == user.id))
        orm_user = result.scalar_one_or_none()
        if not orm_user:
            return None
        
        orm_user.username = user.username
        orm_user.email = user.email
        orm_user.display_name = user.display_name
        orm_user.avatar_url = user.avatar_url
        orm_user.bio = user.bio
        # flush, not commit: get_db() owns the transaction and commits once the
        # request succeeds. Committing here makes a partial update durable even
        # if the rest of the request then fails, so nothing can be rolled back.
        await self.session.flush()
        return self._to_domain(orm_user)

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
    async def update_last_seen(
        self, user_id: uuid.UUID, timestamp: datetime, stale_before: datetime | None = None
    ) -> None:
        # One conditional UPDATE rather than SELECT-then-mutate. Two concurrent
        # requests that both read the same stale last_seen_at would otherwise
        # both write; here the second matches zero rows and costs nothing.
        stmt = update(UserORM).where(UserORM.id == user_id).values(last_seen_at=timestamp)
        if stale_before is not None:
            stmt = stmt.where(
                or_(UserORM.last_seen_at.is_(None), UserORM.last_seen_at < stale_before)
            )
        await self.session.execute(stmt)
    

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, username: str, email: str, password_hash: str) -> User:
        orm_user = UserORM(username=username, email=email, password_hash=password_hash)
        self.session.add(orm_user)
        try:
            # flush, not commit: get_db() owns the transaction and commits once
            # the request succeeds. The flush is still needed here so the server
            # defaults (id, status, created_at) come back populated, and so a
            # unique violation surfaces now rather than at request teardown.
            await self.session.flush()
        except IntegrityError as exc:
            # Translate the driver error at the boundary; nothing above this
            # layer should have to know what SQLAlchemy or Postgres raise.
            detail = str(exc.orig).lower()
            raise UserAlreadyExistsError("email" if "email" in detail else "username") from exc
        return self._to_domain(orm_user)

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