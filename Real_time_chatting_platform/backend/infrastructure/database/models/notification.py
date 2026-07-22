from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class Notification(Base, CreatedAtMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('new_message', 'friend_request', 'system_announcement', 'background_task')",
            name="chk_notifications_type",
        ),
        Index(
            "idx_notifications_user_unread",
            "user_id",
            "is_read",
            postgresql_where=text("is_read = false"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    is_read: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    # created_at inherited from CreatedAtMixin

    user: Mapped["User"] = relationship()