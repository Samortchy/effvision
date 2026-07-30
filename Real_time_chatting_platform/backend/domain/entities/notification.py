from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
import uuid

# Mirrors the chk_notifications_type CHECK constraint on the notifications table.
NotificationType = Literal["new_message", "friend_request", "system_announcement", "background_task"]


@dataclass
class Notification:
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    payload: dict[str, Any]
    is_read: bool
    created_at: datetime
