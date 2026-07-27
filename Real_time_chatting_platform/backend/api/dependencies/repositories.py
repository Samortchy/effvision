from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from infrastructure.database.sessions import get_db
from domain.repositories.user_repository import UserRepository
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from infrastructure.repositories.user_repository_sqla import SQLAlchemyUserRepository
from infrastructure.repositories.refresh_token_repository_sqla import SQLAlchemyRefreshTokenRepository


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SQLAlchemyUserRepository(session)


def get_refresh_token_repository(session: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return SQLAlchemyRefreshTokenRepository(session)