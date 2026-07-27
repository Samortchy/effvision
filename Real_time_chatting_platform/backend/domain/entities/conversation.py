from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import uuid


@dataclass
class Conversation:
    id: uuid.UUID
    type: Literal["public", "private", "group"]
    name: str | None
    description: str | None
    avatar_url: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime