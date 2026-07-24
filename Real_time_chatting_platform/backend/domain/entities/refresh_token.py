from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class RefreshToken:
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    revoked: bool
    created_at: datetime