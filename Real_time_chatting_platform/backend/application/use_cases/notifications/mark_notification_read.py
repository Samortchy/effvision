from __future__ import annotations
import uuid

from domain.exceptions import NotificationNotFoundError, NotNotificationOwnerError
from domain.repositories.notification_repository import NotificationRepository


class MarkNotificationReadUseCase:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def execute(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
        notification = await self.notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError("Notification not found")
        if notification.user_id != user_id:
            raise NotNotificationOwnerError("This notification belongs to another user")

        await self.notification_repo.mark_as_read(notification_id)
