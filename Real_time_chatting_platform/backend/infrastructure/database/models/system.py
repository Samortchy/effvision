from __future__ import annotations
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User


class SystemAnnouncement(Base, CreatedAtMixin):
    __tablename__ = "system_announcements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # created_at inherited from CreatedAtMixin

    creator: Mapped["User | None"] = relationship()