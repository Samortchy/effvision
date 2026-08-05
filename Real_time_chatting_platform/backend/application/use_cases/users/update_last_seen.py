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
        stale_before = now - _THROTTLE_WINDOW

        # Fast path, on the value already loaded by the auth dependency: skip
        # the statement entirely. This is what keeps an ordinary GET from being
        # upgraded into a read-write transaction on every single request.
        if current_last_seen_at is not None and current_last_seen_at > stale_before:
            return

        # The repository re-applies the same bound in SQL. The check above races
        # — several concurrent requests all read the same stale last_seen_at and
        # all decide to write — so the guard has to exist where the write does.
        await self.user_repo.update_last_seen(user_id, now, stale_before)