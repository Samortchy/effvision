from __future__ import annotations
from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field

from application.dto.user_dto import UserSummary
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

    # The other participant, for `type == "private"` only — null otherwise.
    #
    # A private conversation has no server-side `name`, so without this there is
    # nothing in the payload a client could render as a title. It used to be
    # supplied entirely client-side (remembered from the user search that
    # started the conversation), which meant it vanished on logout and never
    # existed at all on a second device: the sidebar fell back to showing a
    # truncated conversation id.
    #
    # Deliberately not populated for public/group conversations. Those can have
    # thousands of members and inlining the roster into every list response
    # would be wasteful — GET /conversations/{id}/members exists for that.
    peer: UserSummary | None = None


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


class CreateGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    # Optional: a group can be created empty and filled later. The creator is
    # never listed here — they are added as owner regardless.
    member_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID
    # Owner is not offered: granting ownership is ChangeMemberRole's job, which
    # enforces the last-owner rule this path knows nothing about.
    role: Literal["admin", "member"] = "member"


class MessageHistoryQuery(BaseModel):
    before: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ChangeMemberRoleRequest(BaseModel):
    role: Role
