from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict

from domain.entities.notification import NotificationType


class NotificationEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_category: Literal["notification"] = "notification"
    id: uuid.UUID
    type: NotificationType
    payload: dict[str, Any]
    created_at: datetime


class SystemAnnouncementEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_category: Literal["system_announcement"] = "system_announcement"
    id: uuid.UUID
    title: str
    body: str
    created_at: datetime


StreamedEvent = NotificationEvent | SystemAnnouncementEvent
