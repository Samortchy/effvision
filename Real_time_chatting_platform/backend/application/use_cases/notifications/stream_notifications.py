from __future__ import annotations
import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timezone
import uuid

from application.dto.notification_dto import NotificationEvent, StreamedEvent, SystemAnnouncementEvent
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.system_announcement_repository import SystemAnnouncementRepository

_POLL_INTERVAL_SECONDS = 2.0

# Most events either source will hand back in a single poll. A live stream never
# comes near it; it matters for a client resuming from an old Last-Event-ID,
# whose backlog would otherwise be loaded in one unbounded query. A truncated
# poll is the front of the backlog, so the rest arrives on the polls after it.
_MAX_EVENTS_PER_POLL = 100

# A callable handing back a *fresh* pair of repositories bound to a short-lived
# unit of work. The stream must not hold one for its whole lifetime: an SSE
# connection stays open for hours, and a repository backed by a pooled DB
# connection would pin that connection (and an open transaction) the entire time.
RepositoriesProvider = Callable[
    [], AbstractAsyncContextManager[tuple[NotificationRepository, SystemAnnouncementRepository]]
]


class StreamNotificationsUseCase:
    def __init__(
        self,
        open_repositories: RepositoriesProvider,
        poll_interval_seconds: float = _POLL_INTERVAL_SECONDS,
        max_events_per_poll: int = _MAX_EVENTS_PER_POLL,
    ):
        self.open_repositories = open_repositories
        self.poll_interval_seconds = poll_interval_seconds
        self.max_events_per_poll = max_events_per_poll

    async def stream(
        self, user_id: uuid.UUID, since: datetime | None = None
    ) -> AsyncGenerator[StreamedEvent, None]:
        """Yields the user's notifications and global announcements as they appear,
        oldest first.

        `since` resumes a dropped connection (from the client's Last-Event-ID);
        None starts from now and only delivers events created from here on.

        Delivery is at-least-once: the cursor is a timestamp, so an event sharing
        its timestamp with the resume point can be redelivered once after a
        reconnect. Clients de-duplicate on the event id.
        """
        cursor = since if since is not None else datetime.now(timezone.utc)
        # Ids already delivered *at exactly* `cursor`. Because the repository
        # bound is inclusive, this is what stops the boundary event from
        # repeating on every poll of a live connection.
        delivered_at_cursor: set[uuid.UUID] = set()

        while True:
            limit = self.max_events_per_poll
            async with self.open_repositories() as (notification_repo, announcement_repo):
                notifications = await notification_repo.get_new_since(user_id, cursor, limit)
                announcements = await announcement_repo.get_new_since(cursor, limit)

            # The unit of work is closed before anything is yielded — a slow or
            # stalled client applies back-pressure here, and must not do so while
            # holding a database connection.
            events: list[StreamedEvent] = [
                *(NotificationEvent.model_validate(n) for n in notifications),
                *(SystemAnnouncementEvent.model_validate(a) for a in announcements),
            ]
            # Merge the two sources into one time-ordered stream so the cursor the
            # client echoes back is monotonic. Interleaving them unsorted would let
            # a later notification's timestamp become the resume point while an
            # earlier announcement was still unsent, silently dropping it.
            events.sort(key=lambda event: event.created_at)

            # The same hazard, now from truncation rather than ordering. If one
            # source came back full it has more behind it, and everything past its
            # last row is unknown territory — yielding a *later* event from the
            # other source would push the cursor beyond rows never delivered. So
            # this poll stops at the earliest such horizon and resumes there.
            horizon = min(
                (
                    batch[-1].created_at
                    for batch in (notifications, announcements)
                    if len(batch) >= limit
                ),
                default=None,
            )
            truncated = horizon is not None
            if truncated:
                events = [event for event in events if event.created_at <= horizon]

            fresh = [event for event in events if event.id not in delivered_at_cursor]
            for event in fresh:
                yield event

            advanced = False
            if fresh:
                newest = fresh[-1].created_at
                if newest > cursor:
                    cursor = newest
                    delivered_at_cursor = {e.id for e in fresh if e.created_at == newest}
                    advanced = True
                else:
                    delivered_at_cursor.update(e.id for e in fresh)

            # Draining a backlog: go straight back for the next page instead of
            # trickling it out at one page per poll interval.
            #
            # Gated on the cursor having actually moved. A full page that does not
            # advance it means more than `limit` events share a single timestamp —
            # the query would return the same page forever, and skipping the sleep
            # would turn that into a hot loop against the database. Falling back to
            # the normal interval keeps it a slow stream rather than an outage.
            if truncated and advanced:
                continue

            await asyncio.sleep(self.poll_interval_seconds)
