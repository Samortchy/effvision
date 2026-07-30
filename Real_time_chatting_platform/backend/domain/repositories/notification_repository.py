from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any
import uuid

from domain.entities.notification import Notification, NotificationType


class NotificationRepository(ABC):
    """Port for notification persistence."""

    @abstractmethod
    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        ...

    @abstractmethod
    async def get_new_since(self, user_id: uuid.UUID, since: datetime | None) -> list[Notification]:
        """Rows with created_at >= since, oldest first. The bound is *inclusive*
        so that rows sharing a timestamp with the caller's cursor aren't skipped;
        callers de-duplicate by id."""
        ...

    @abstractmethod
    async def create_many(
        self, user_ids: Sequence[uuid.UUID], type: NotificationType, payload: dict[str, Any]
    ) -> list[Notification]:
        """Fan one event out to many recipients in a single insert.
        Returns [] when user_ids is empty."""
        ...

    @abstractmethod
    async def mark_as_read(self, notification_id: uuid.UUID) -> None:
        ...
