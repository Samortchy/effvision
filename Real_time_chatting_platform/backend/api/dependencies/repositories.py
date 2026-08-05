from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from infrastructure.database.sessions import AsyncSessionLocal, get_db
from domain.repositories.user_repository import UserRepository
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository
from infrastructure.repositories.user_repository_sqla import SQLAlchemyUserRepository
from infrastructure.repositories.refresh_token_repository_sqla import SQLAlchemyRefreshTokenRepository
from infrastructure.repositories.conversation_repository_sqla import SQLAlchemyConversationRepository
from infrastructure.repositories.message_repository_sqla import SQLAlchemyMessageRepository
from domain.repositories.broadcaster import Broadcaster
from domain.repositories.friend_repository import FriendRepository
from infrastructure.repositories.friend_repository_sqla import SQLAlchemyFriendRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.system_announcement_repository import SystemAnnouncementRepository
from infrastructure.repositories.notification_repository_sqla import SQLAlchemyNotificationRepository
from infrastructure.repositories.system_announcement_repository_sqla import SQLAlchemySystemAnnouncementRepository
from infrastructure.websocket.broadcaster import WebSocketBroadcaster


def get_notification_repository(session: AsyncSession = Depends(get_db)) -> NotificationRepository:
    return SQLAlchemyNotificationRepository(session)


@asynccontextmanager
async def open_notification_repositories() -> AsyncIterator[
    tuple[NotificationRepository, SystemAnnouncementRepository]
]:
    """A self-contained unit of work for the SSE stream.

    Deliberately *not* a Depends() provider. FastAPI tears down `yield`
    dependencies before the response body is streamed, so a session from
    `get_db` is already committed and closed by the time an SSE generator runs.
    The stream opens one of these per poll instead, returning the connection to
    the pool between polls rather than pinning it for the life of the connection.
    """
    async with AsyncSessionLocal() as session:
        yield (
            SQLAlchemyNotificationRepository(session),
            SQLAlchemySystemAnnouncementRepository(session),
        )


@asynccontextmanager
async def open_conversation_repository() -> AsyncIterator[ConversationRepository]:
    """A self-contained unit of work for the WebSocket endpoint.

    Same reasoning as open_notification_repositories: a Depends() provider hands
    the endpoint one session, and a WebSocket endpoint does not return for as
    long as the socket is open — hours. That would pin a pooled connection and
    an idle transaction for the whole conversation. Opening one of these per
    inbound frame returns the connection to the pool in between.
    """
    async with AsyncSessionLocal() as session:
        yield SQLAlchemyConversationRepository(session)


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SQLAlchemyUserRepository(session)


def get_friend_repository(session: AsyncSession = Depends(get_db)) -> FriendRepository:
    return SQLAlchemyFriendRepository(session)


def get_refresh_token_repository(session: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return SQLAlchemyRefreshTokenRepository(session)


def get_conversation_repository(session: AsyncSession = Depends(get_db)) -> ConversationRepository:
    return SQLAlchemyConversationRepository(session)


def get_message_repository(session: AsyncSession = Depends(get_db)) -> MessageRepository:
    return SQLAlchemyMessageRepository(session)


def get_broadcaster() -> Broadcaster:
    """The real-time fan-out adapter.

    Takes no session: it talks to the in-process socket registry, not the
    database. A Depends() provider all the same, so a test can override it with
    a double instead of opening real WebSockets.
    """
    return WebSocketBroadcaster()
