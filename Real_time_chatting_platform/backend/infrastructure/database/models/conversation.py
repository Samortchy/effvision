from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from infrastructure.database.models.user import User
    from infrastructure.database.models.message import Message


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("type IN ('public', 'private', 'group')", name="chk_conversations_type"),
        Index(
            "idx_conversations_single_public",
            "type",
            unique=True,
            postgresql_where=text("type = 'public'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    type: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str | None]
    description: Mapped[str | None]
    avatar_url: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # created_at, updated_at inherited from TimestampMixin

    creator: Mapped["User | None"] = relationship()
    members: Mapped[list["ConversationMember"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMember(Base):
    __tablename__ = "conversation_members"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'admin', 'member')", name="chk_members_role"),
        UniqueConstraint("conversation_id", "user_id", name="uq_conversation_member"),
        Index("idx_conversation_members_user", "user_id"),
        Index("idx_conversation_members_conversation", "conversation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False, server_default="member")
    joined_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    left_at: Mapped[datetime | None]
    muted: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL")
    )
    last_read_at: Mapped[datetime | None]

    conversation: Mapped["Conversation"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="conversation_memberships")