from __future__ import annotations
from pydantic import BaseModel, Field

from uuid import UUID
from datetime import datetime


class MessageSearchQuery(BaseModel):
    q: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    is_edited: bool = False
    edited_at: datetime | None = None
    created_at: datetime | None = None

class EditMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)