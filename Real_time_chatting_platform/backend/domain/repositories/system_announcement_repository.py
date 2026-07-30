from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.system_announcement import SystemAnnouncement


class SystemAnnouncementRepository(ABC):
    """Port for system announcement persistence (read-only for this task —
    creating announcements is out of scope per the sprint plan)."""

    @abstractmethod
    async def get_new_since(self, since: datetime | None) -> list[SystemAnnouncement]:
        """Rows with created_at >= since, oldest first. Inclusive bound — see
        NotificationRepository.get_new_since."""
        ...