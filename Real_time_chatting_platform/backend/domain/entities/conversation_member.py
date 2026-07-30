from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import uuid

# Single source of truth for membership roles — imported by the membership
# rules, the use cases and the DTOs so the three can never drift apart.
Role = Literal["owner", "admin", "member"]


@dataclass
class ConversationMember:
    id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    role: Role
    joined_at: datetime
    left_at: datetime | None
    muted: bool
    last_read_message_id: uuid.UUID | None
    last_read_at: datetime | None
