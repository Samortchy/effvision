from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class SystemAnnouncement:
    id: uuid.UUID
    title: str
    body: str
    created_by: uuid.UUID | None
    created_at: datetime