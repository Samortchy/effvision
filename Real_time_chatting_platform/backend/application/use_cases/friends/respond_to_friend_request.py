from __future__ import annotations
from datetime import datetime, timezone
import uuid

import structlog

from domain.entities.friend import FriendRequest
from domain.exceptions import (
    FriendRequestAlreadyAnsweredError,
    FriendRequestNotFoundError,
    NotFriendRequestRecipientError,
)
from domain.repositories.friend_repository import FriendRepository

logger = structlog.get_logger()


class RespondToFriendRequestUseCase:
    """Accept or decline a request that was sent to you.

    Accepting does two writes — the status change and the friendship row — in
    one unit of work. Split across two, a failure between them would leave a
    request marked accepted with no friendship to show for it, and no way for
    either user to retry: the request is no longer pending, so it can never be
    accepted again.
    """

    def __init__(self, friend_repo: FriendRepository):
        self.friend_repo = friend_repo

    async def execute(
        self, request_id: uuid.UUID, responding_user_id: uuid.UUID, accept: bool
    ) -> FriendRequest:
        request = await self.friend_repo.get_request_by_id(request_id)
        if request is None:
            raise FriendRequestNotFoundError("Friend request not found")

        # Only the recipient may answer. The sender cancelling their own request
        # is a different action, and 'declined' would misrepresent it.
        if request.recipient_id != responding_user_id:
            raise NotFriendRequestRecipientError("This request was not sent to you")

        if request.status != "pending":
            raise FriendRequestAlreadyAnsweredError(
                f"This request has already been {request.status}"
            )

        now = datetime.now(timezone.utc)
        updated = await self.friend_repo.set_request_status(
            request_id, "accepted" if accept else "declined", now
        )

        if accept:
            # Guarded because the pair could already be friends via another
            # route (a second request accepted moments earlier); the unique
            # constraint would otherwise turn that race into a 500.
            if not await self.friend_repo.are_friends(request.sender_id, request.recipient_id):
                await self.friend_repo.create_friendship(request.sender_id, request.recipient_id)

        logger.info(
            "friend_request_answered",
            request_id=str(request_id),
            accepted=accept,
            responder_id=str(responding_user_id),
        )
        return updated
