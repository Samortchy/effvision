from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from infrastructure.database.sessions import get_db
from domain.repositories.user_repository import UserRepository
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository
from infrastructure.repositories.user_repository_sqla import SQLAlchemyUserRepository
from infrastructure.repositories.refresh_token_repository_sqla import SQLAlchemyRefreshTokenRepository
from infrastructure.repositories.conversation_repository_sqla import SQLAlchemyConversationRepository
from infrastructure.repositories.message_repository_sqla import SQLAlchemyMessageRepository


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SQLAlchemyUserRepository(session)


def get_refresh_token_repository(session: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return SQLAlchemyRefreshTokenRepository(session)


def get_conversation_repository(session: AsyncSession = Depends(get_db)) -> ConversationRepository:
    return SQLAlchemyConversationRepository(session)


def get_message_repository(session: AsyncSession = Depends(get_db)) -> MessageRepository:
    return SQLAlchemyMessageRepository(session)
