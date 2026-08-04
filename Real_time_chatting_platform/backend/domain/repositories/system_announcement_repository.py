from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.system_announcement import SystemAnnouncement


class SystemAnnouncementRepository(ABC):
    """Port for system announcement persistence (read-only for this task —
    creating announcements is out of scope per the sprint plan)."""

    @abstractmethod
    async def get_new_since(
        self, since: datetime | None, limit: int = 100
    ) -> list[SystemAnnouncement]:
        """Rows with created_at >= since, oldest first, at most `limit` of them.
        Inclusive bound and bounded for the same reasons — see
        NotificationRepository.get_new_since."""
        ...