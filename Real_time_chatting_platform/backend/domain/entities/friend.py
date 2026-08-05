from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import uuid

FriendRequestStatus = Literal["pending", "accepted", "declined"]


@dataclass
class FriendRequest:
    id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    status: FriendRequestStatus
    responded_at: datetime | None
    created_at: datetime


@dataclass
class Friendship:
    """A mutual friendship.

    Stored with a canonical ordering — the table carries
    `CHECK (user_id_a < user_id_b)` — so that one relationship can only ever be
    one row. Without that, (A,B) and (B,A) would both be insertable and the
    unique constraint on the pair would mean nothing.

    Callers should not care which of the two they are; use `other_than()`.
    """

    id: uuid.UUID
    user_id_a: uuid.UUID
    user_id_b: uuid.UUID
    created_at: datetime

    def other_than(self, user_id: uuid.UUID) -> uuid.UUID:
        return self.user_id_b if user_id == self.user_id_a else self.user_id_a


def canonical_pair(x: uuid.UUID, y: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Order two user ids the way the friendships table requires.

    Python compares UUIDs by their 128-bit integer value and Postgres compares
    them bytewise big-endian — the same ordering, so a pair sorted here still
    satisfies the CHECK constraint on the way in.
    """
    return (x, y) if x < y else (y, x)
