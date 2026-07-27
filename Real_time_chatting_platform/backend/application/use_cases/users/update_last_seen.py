from __future__ import annotations
from datetime import datetime, timedelta, timezone
import uuid

from domain.repositories.user_repository import UserRepository

_THROTTLE_WINDOW = timedelta(seconds=60)


class UpdateLastSeenUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, user_id: uuid.UUID, current_last_seen_at: datetime | None) -> None:
        now = datetime.now(timezone.utc)

        if current_last_seen_at is not None and (now - current_last_seen_at) < _THROTTLE_WINDOW:
            return  # too recent, skip the write

        await self.user_repo.update_last_seen(user_id, now)