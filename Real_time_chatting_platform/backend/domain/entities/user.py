from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import uuid


@dataclass
class User:
    id: uuid.UUID
    username: str
    email: str
    password_hash: str
    display_name: str | None
    avatar_url: str | None
    bio: str | None
    status: Literal["online", "offline", "away"]
    last_seen_at: datetime | None
    created_at: datetime