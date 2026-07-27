from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class Message:
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID | None
    content: str
    is_edited: bool
    edited_at: datetime | None
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime