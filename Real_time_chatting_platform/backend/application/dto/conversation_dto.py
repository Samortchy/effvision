from __future__ import annotations
from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field

from domain.entities.conversation_member import Role


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: Literal["public", "private", "group"]
    name: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ConversationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    role: Role
    joined_at: datetime
    muted: bool


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID | None
    content: str
    is_edited: bool
    edited_at: datetime | None
    created_at: datetime


class StartPrivateConversationRequest(BaseModel):
    recipient_id: uuid.UUID


class MessageHistoryQuery(BaseModel):
    before: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ChangeMemberRoleRequest(BaseModel):
    role: Role
