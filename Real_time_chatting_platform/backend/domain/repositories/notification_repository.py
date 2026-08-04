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
    async def get_new_since(
        self, user_id: uuid.UUID, since: datetime | None, limit: int = 100
    ) -> list[Notification]:
        """Rows with created_at >= since, oldest first, at most `limit` of them.

        The bound is *inclusive* so that rows sharing a timestamp with the
        caller's cursor aren't skipped; callers de-duplicate by id.

        `limit` is not optional in spirit: this is polled every couple of seconds
        by the SSE stream, and a client resuming from an old Last-Event-ID would
        otherwise pull its entire notification history into memory in one query.
        Oldest-first ordering means a truncated result is the *front* of the
        backlog, so the caller drains the rest by advancing its cursor."""
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
