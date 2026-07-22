from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class FriendRequest(Base, CreatedAtMixin):
    __tablename__ = "friend_requests"
    __table_args__ = (
        CheckConstraint("sender_id <> recipient_id", name="chk_no_self_request"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined')", name="chk_friend_requests_status"
        ),
        Index(
            "idx_friend_requests_pending_pair",
            "sender_id",
            "recipient_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("idx_friend_requests_recipient", "recipient_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default="pending")
    responded_at: Mapped[datetime | None]
    # created_at inherited from CreatedAtMixin

    sender: Mapped["User"] = relationship(foreign_keys=[sender_id])
    recipient: Mapped["User"] = relationship(foreign_keys=[recipient_id])


class Friendship(Base, CreatedAtMixin):
    __tablename__ = "friendships"
    __table_args__ = (
        CheckConstraint("user_id_a < user_id_b", name="chk_friendship_order"),
        UniqueConstraint("user_id_a", "user_id_b", name="uq_friendship_pair"),
        Index("idx_friendships_a", "user_id_a"),
        Index("idx_friendships_b", "user_id_b"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id_a: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user_id_b: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # created_at inherited from CreatedAtMixin

    user_a: Mapped["User"] = relationship(foreign_keys=[user_id_a])
    user_b: Mapped["User"] = relationship(foreign_keys=[user_id_b])