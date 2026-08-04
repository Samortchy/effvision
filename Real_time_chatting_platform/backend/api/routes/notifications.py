from __future__ import annotations
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from api.dependencies.auth import get_current_user, get_current_user_sse
from api.dependencies.repositories import get_notification_repository, open_notification_repositories
from application.use_cases.notifications.mark_notification_read import MarkNotificationReadUseCase
from application.use_cases.notifications.stream_notifications import StreamNotificationsUseCase
from domain.entities.user import User
from domain.exceptions import NotificationNotFoundError, NotNotificationOwnerError
from domain.repositories.notification_repository import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Comment frames on an idle stream, so an intermediary proxy does not decide the
# connection is dead and drop it silently. This is sse-starlette's own default;
# stated explicitly because the behaviour is load-bearing here.
PING_INTERVAL_SECONDS = 15

# Ceiling on a single send. Generous — this is a stuck-socket backstop, not a
# latency budget.
SEND_TIMEOUT_SECONDS = 30.0


def _parse_last_event_id(last_event_id: str | None) -> datetime | None:
    """The stream's event ids are ISO-8601 timestamps, so the Last-Event-ID a
    client replays on reconnect doubles as its resume cursor. A malformed value
    is ignored rather than rejected — the worst case is missing whatever arrived
    while disconnected, which beats refusing the connection outright."""
    if not last_event_id:
        return None
    try:
        resume_from = datetime.fromisoformat(last_event_id)
    except ValueError:
        return None
    # A naive value can't be ordered against TIMESTAMPTZ columns; assume UTC.
    return resume_from if resume_from.tzinfo else resume_from.replace(tzinfo=timezone.utc)


@router.get("/stream")
async def stream_notifications(
    request: Request,
    current_user: User = Depends(get_current_user_sse),
) -> EventSourceResponse:
    # No repository Depends() here: FastAPI closes yield-dependencies before the
    # body is streamed, so the use case opens its own short-lived unit of work
    # per poll (see open_notification_repositories).
    use_case = StreamNotificationsUseCase(open_notification_repositories)
    since = _parse_last_event_id(request.headers.get("last-event-id"))

    async def event_generator():
        async for event in use_case.stream(current_user.id, since):
            yield {
                # Echoed back as Last-Event-ID on reconnect.
                "id": event.created_at.isoformat(),
                "event": event.event_category,
                "data": event.model_dump_json(),
            }

    # Backstops against a stream that stops going anywhere. Note what is NOT
    # here: a `request.is_disconnected()` check in the generator. EventSourceResponse
    # already runs listen_for_disconnect(), which awaits receive() and cancels the
    # task group; calling is_disconnected() would put a second consumer on the same
    # ASGI receive channel, and whichever coroutine happened to be waiting would
    # swallow the http.disconnect the other one needed. That makes the leak more
    # likely, not less.
    #
    # What is missing by default is send_timeout: it is None out of the box, and
    # stream_response wraps each send in anyio.move_on_after(send_timeout), which
    # never fires for None. A client that stops reading its socket then blocks that
    # send forever and pins the task, the generator and its poll loop. A finite
    # timeout turns that into a SendTimeoutError that tears the stream down.
    return EventSourceResponse(
        event_generator(),
        ping=PING_INTERVAL_SECONDS,
        send_timeout=SEND_TIMEOUT_SECONDS,
    )


@router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> None:
    use_case = MarkNotificationReadUseCase(notification_repo)
    try:
        await use_case.execute(notification_id, current_user.id)
    except NotificationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotNotificationOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
