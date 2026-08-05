from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal
import uuid

from domain.entities.friend import FriendRequest, FriendRequestStatus, Friendship
from domain.entities.user import User

Direction = Literal["incoming", "outgoing"]


class FriendRepository(ABC):
    """Port for friend requests and friendships."""

    # --- requests --------------------------------------------------------

    @abstractmethod
    async def get_request_by_id(self, request_id: uuid.UUID) -> FriendRequest | None:
        ...

    @abstractmethod
    async def get_pending_request(
        self, sender_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> FriendRequest | None:
        """The pending request in *that direction only*.

        Direction matters: "I already asked them" and "they already asked me"
        are different situations needing different answers, so callers check
        each one separately rather than getting whichever exists.
        """
        ...

    @abstractmethod
    async def create_request(
        self, sender_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> FriendRequest:
        ...

    @abstractmethod
    async def set_request_status(
        self, request_id: uuid.UUID, status: FriendRequestStatus, responded_at: datetime
    ) -> FriendRequest:
        """Raises FriendRequestNotFoundError if there is no such request."""
        ...

    @abstractmethod
    async def list_requests(
        self, user_id: uuid.UUID, direction: Direction
    ) -> list[tuple[FriendRequest, User]]:
        """Pending requests, each paired with the *other* party.

        The counterpart comes back in the same query rather than being looked up
        per row — a request list is exactly the screen where an N+1 would show.
        """
        ...

    # --- friendships -----------------------------------------------------

    @abstractmethod
    async def are_friends(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
        ...

    @abstractmethod
    async def create_friendship(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ) -> Friendship:
        """Order-insensitive: the implementation canonicalises the pair to
        satisfy the table's CHECK (user_id_a < user_id_b)."""
        ...

    @abstractmethod
    async def delete_friendship(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
        """Returns False if there was no friendship to remove."""
        ...

    @abstractmethod
    async def list_friends(self, user_id: uuid.UUID) -> list[User]:
        """The users this person is friends with, alphabetically by username."""
        ...
