from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("idx_user_sessions_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    connected_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    disconnected_at: Mapped[datetime | None]
    client_info: Mapped[str | None]
    # No created_at — connected_at is this table's creation timestamp.

    user: Mapped["User"] = relationship()