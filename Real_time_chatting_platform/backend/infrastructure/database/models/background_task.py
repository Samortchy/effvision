from __future__ import annotations
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class BackgroundTask(Base, TimestampMixin):
    __tablename__ = "background_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="chk_background_tasks_status",
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="chk_background_tasks_progress"),
        Index("idx_background_tasks_user", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default="pending")
    progress: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # created_at, updated_at inherited from TimestampMixin

    user: Mapped["User"] = relationship()