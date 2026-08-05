from __future__ import annotations
from datetime import datetime
import uuid

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.friend import FriendRequest, FriendRequestStatus, Friendship, canonical_pair
from domain.entities.user import User
from domain.exceptions import FriendRequestNotFoundError
from domain.repositories.friend_repository import Direction, FriendRepository
from infrastructure.database.models.friend import (
    FriendRequest as FriendRequestORM,
    Friendship as FriendshipORM,
)
from infrastructure.database.models.user import User as UserORM
from infrastructure.repositories.user_repository_sqla import SQLAlchemyUserRepository


class SQLAlchemyFriendRepository(FriendRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- requests --------------------------------------------------------

    async def get_request_by_id(self, request_id: uuid.UUID) -> FriendRequest | None:
        result = await self.session.execute(
            select(FriendRequestORM).where(FriendRequestORM.id == request_id)
        )
        row = result.scalar_one_or_none()
        return self._request_to_entity(row) if row else None

    async def get_pending_request(
        self, sender_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> FriendRequest | None:
        result = await self.session.execute(
            select(FriendRequestORM).where(
                FriendRequestORM.sender_id == sender_id,
                FriendRequestORM.recipient_id == recipient_id,
                FriendRequestORM.status == "pending",
            )
        )
        row = result.scalar_one_or_none()
        return self._request_to_entity(row) if row else None

    async def create_request(
        self, sender_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> FriendRequest:
        row = FriendRequestORM(sender_id=sender_id, recipient_id=recipient_id, status="pending")
        self.session.add(row)
        await self.session.flush()
        # id, status and created_at are server-side defaults.
        await self.session.refresh(row)
        return self._request_to_entity(row)

    async def set_request_status(
        self, request_id: uuid.UUID, status: FriendRequestStatus, responded_at: datetime
    ) -> FriendRequest:
        result = await self.session.execute(
            select(FriendRequestORM).where(FriendRequestORM.id == request_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise FriendRequestNotFoundError("Friend request not found")

        row.status = status
        row.responded_at = responded_at
        await self.session.flush()
        return self._request_to_entity(row)

    async def list_requests(
        self, user_id: uuid.UUID, direction: Direction
    ) -> list[tuple[FriendRequest, User]]:
        # For an incoming request the counterpart is the sender; for an outgoing
        # one it is the recipient. The join column flips with the direction.
        if direction == "incoming":
            mine, theirs = FriendRequestORM.recipient_id, FriendRequestORM.sender_id
        else:
            mine, theirs = FriendRequestORM.sender_id, FriendRequestORM.recipient_id

        result = await self.session.execute(
            select(FriendRequestORM, UserORM)
            .join(UserORM, UserORM.id == theirs)
            .where(mine == user_id, FriendRequestORM.status == "pending")
            .order_by(FriendRequestORM.created_at.desc())
        )
        return [
            (self._request_to_entity(req), SQLAlchemyUserRepository._to_domain(user))
            for req, user in result.all()
        ]

    # --- friendships -----------------------------------------------------

    async def are_friends(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
        low, high = canonical_pair(user_a_id, user_b_id)
        result = await self.session.execute(
            select(FriendshipORM.id).where(
                FriendshipORM.user_id_a == low,
                FriendshipORM.user_id_b == high,
            )
        )
        return result.scalar_one_or_none() is not None

    async def create_friendship(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ) -> Friendship:
        # Canonicalised here rather than trusting the caller: the table's
        # CHECK (user_id_a < user_id_b) rejects the wrong order outright, and
        # that constraint is what makes "one row per relationship" true.
        low, high = canonical_pair(user_a_id, user_b_id)
        row = FriendshipORM(user_id_a=low, user_id_b=high)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return Friendship(
            id=row.id, user_id_a=row.user_id_a, user_id_b=row.user_id_b, created_at=row.created_at
        )

    async def delete_friendship(self, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
        low, high = canonical_pair(user_a_id, user_b_id)
        result = await self.session.execute(
            delete(FriendshipORM).where(
                FriendshipORM.user_id_a == low,
                FriendshipORM.user_id_b == high,
            )
        )
        return result.rowcount > 0

    async def list_friends(self, user_id: uuid.UUID) -> list[User]:
        # The caller may sit on either side of the canonical pair, so the join
        # picks whichever column is *not* them.
        result = await self.session.execute(
            select(UserORM)
            .join(
                FriendshipORM,
                or_(
                    (FriendshipORM.user_id_a == user_id) & (FriendshipORM.user_id_b == UserORM.id),
                    (FriendshipORM.user_id_b == user_id) & (FriendshipORM.user_id_a == UserORM.id),
                ),
            )
            .order_by(UserORM.username.asc())
        )
        return [SQLAlchemyUserRepository._to_domain(u) for u in result.scalars().all()]

    # --- mapping ---------------------------------------------------------

    @staticmethod
    def _request_to_entity(row: FriendRequestORM) -> FriendRequest:
        return FriendRequest(
            id=row.id,
            sender_id=row.sender_id,
            recipient_id=row.recipient_id,
            status=row.status,
            responded_at=row.responded_at,
            created_at=row.created_at,
        )
