from __future__ import annotations
import uuid

import structlog

from domain.entities.friend import FriendRequest
from domain.entities.user import User
from domain.exceptions import NotFriendsError
from domain.repositories.friend_repository import Direction, FriendRepository

logger = structlog.get_logger()


class ListFriendsUseCase:
    def __init__(self, friend_repo: FriendRepository):
        self.friend_repo = friend_repo

    async def execute(self, user_id: uuid.UUID) -> list[User]:
        return await self.friend_repo.list_friends(user_id)


class ListFriendRequestsUseCase:
    """Pending requests in one direction, each with the other party attached."""

    def __init__(self, friend_repo: FriendRepository):
        self.friend_repo = friend_repo

    async def execute(
        self, user_id: uuid.UUID, direction: Direction
    ) -> list[tuple[FriendRequest, User]]:
        return await self.friend_repo.list_requests(user_id, direction)


class RemoveFriendUseCase:
    """Unfriend. Symmetric — either side may do it, and it ends for both.

    Deliberately leaves the answered request rows alone: they are a record of
    what happened, and because the unique index on a pending pair is partial,
    keeping them does not stop a future request between the same two people.
    """

    def __init__(self, friend_repo: FriendRepository):
        self.friend_repo = friend_repo

    async def execute(self, user_id: uuid.UUID, friend_id: uuid.UUID) -> None:
        removed = await self.friend_repo.delete_friendship(user_id, friend_id)
        if not removed:
            raise NotFriendsError("You are not friends with this user")

        logger.info("friendship_removed", user_id=str(user_id), friend_id=str(friend_id))
