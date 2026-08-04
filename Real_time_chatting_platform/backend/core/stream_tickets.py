"""Short-lived, single-use tickets for authenticating EventSource streams.

The browser's EventSource API cannot set an Authorization header, so an SSE
endpoint has to take its credential from the URL. Putting the *access token*
there means a 15-minute bearer credential ends up in the server's access log,
every proxy log on the path, and the browser's history — and it is replayable by
anyone who reads any of those.

A ticket is the same idea with the blast radius removed: it authenticates
exactly one stream, it is void after a few seconds, and redeeming it destroys
it. A ticket recovered from a log is worth nothing by the time it is read.

Scope: this store is per-process, in memory. Deliberate — tickets live for
seconds and there is nothing worth persisting. It does mean that under multiple
worker processes a ticket must be redeemed by the same worker that issued it;
moving to more than one worker means moving this to Redis.
"""
from __future__ import annotations

import secrets
import time
import uuid

# How long a ticket stays valid. Long enough to cover minting it and opening the
# stream on a slow connection, short enough that a leaked one is already dead.
TICKET_TTL_SECONDS = 30

# ticket -> (user_id, expires_at monotonic seconds)
_tickets: dict[str, tuple[uuid.UUID, float]] = {}


def _purge_expired(now: float) -> None:
    for ticket in [t for t, (_, expires_at) in _tickets.items() if expires_at <= now]:
        _tickets.pop(ticket, None)


def issue(user_id: uuid.UUID) -> str:
    """Mint a ticket for a user who has *already* authenticated by header."""
    now = time.monotonic()
    _purge_expired(now)

    ticket = secrets.token_urlsafe(32)
    _tickets[ticket] = (user_id, now + TICKET_TTL_SECONDS)
    return ticket


def redeem(ticket: str | None) -> uuid.UUID | None:
    """Consume a ticket, returning the user it was issued to.

    Single-use: the entry is removed whether or not it turns out to be expired,
    so the same ticket can never open a second stream.
    """
    if not ticket:
        return None

    now = time.monotonic()
    _purge_expired(now)

    entry = _tickets.pop(ticket, None)
    if entry is None:
        return None

    user_id, expires_at = entry
    return user_id if expires_at > now else None
