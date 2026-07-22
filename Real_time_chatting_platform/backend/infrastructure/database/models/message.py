from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Computed, ForeignKey, Index, desc, text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from infrastructure.database.models.conversation import Conversation
    from infrastructure.database.models.user import User


class Message(Base, CreatedAtMixin):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation_created", "conversation_id", desc("created_at")),
        Index("idx_messages_sender", "sender_id"),
        Index("idx_messages_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    content: Mapped[str] = mapped_column(nullable=False)
    is_edited: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    edited_at: Mapped[datetime | None]
    is_deleted: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None]
    # created_at inherited from CreatedAtMixin

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(content, ''))", persisted=True),
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    sender: Mapped["User | None"] = relationship()