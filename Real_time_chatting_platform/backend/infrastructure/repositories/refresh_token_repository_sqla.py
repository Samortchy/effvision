from __future__ import annotations
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.refresh_token import RefreshToken
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from infrastructure.database.models.user import RefreshToken as RefreshTokenORM


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepository):
    """Concrete implementation of RefreshTokenRepository, backed by Postgres."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        orm_token = RefreshTokenORM(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(orm_token)
        await self.session.flush()  # assigns the DB-generated id without committing yet
        return self._to_domain(orm_token)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
        )
        orm_token = result.scalar_one_or_none()
        return self._to_domain(orm_token) if orm_token else None

    async def revoke(self, token_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.id == token_id)
        )
        orm_token = result.scalar_one_or_none()
        if orm_token:
            orm_token.revoked = True
            await self.session.flush()

    @staticmethod
    def _to_domain(orm_token: RefreshTokenORM) -> RefreshToken:
        return RefreshToken(
            id=orm_token.id,
            user_id=orm_token.user_id,
            token_hash=orm_token.token_hash,
            expires_at=orm_token.expires_at,
            revoked=orm_token.revoked,
            created_at=orm_token.created_at,
        )