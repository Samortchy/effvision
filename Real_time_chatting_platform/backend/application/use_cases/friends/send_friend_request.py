from __future__ import annotations
import uuid

import structlog

from domain.entities.friend import FriendRequest
from domain.exceptions import (
    AlreadyFriendsError,
    CannotFriendSelfError,
    FriendRequestAlreadySentError,
    IncomingFriendRequestExistsError,
    UserNotFoundError,
)
from domain.repositories.friend_repository import FriendRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.user_repository import UserRepository

logger = structlog.get_logger()


class SendFriendRequestUseCase:
    """Ask someone to be friends.

    The four rejections below are all states the database would also catch, but
    only as an opaque constraint violation. Checking them here is what turns
    each into an answer the client can act on.
    """

    def __init__(
        self,
        friend_repo: FriendRepository,
        user_repo: UserRepository,
        notification_repo: NotificationRepository,
    ):
        self.friend_repo = friend_repo
        self.user_repo = user_repo
        self.notification_repo = notification_repo

    async def execute(self, sender_id: uuid.UUID, recipient_id: uuid.UUID) -> FriendRequest:
        # chk_no_self_request enforces this too; a 400 beats a 500.
        if sender_id == recipient_id:
            raise CannotFriendSelfError("You cannot send yourself a friend request")

        recipient = await self.user_repo.get_by_id(recipient_id)
        if recipient is None:
            raise UserNotFoundError("That user does not exist")

        if await self.friend_repo.are_friends(sender_id, recipient_id):
            raise AlreadyFriendsError("You are already friends with this user")

        # idx_friend_requests_pending_pair covers this direction. Note the index
        # is partial (WHERE status = 'pending'), so a previously declined
        # request does not block a new one — which is deliberate.
        if await self.friend_repo.get_pending_request(sender_id, recipient_id) is not None:
            raise FriendRequestAlreadySentError("You already have a pending request to this user")

        # The mirror case. Auto-accepting here would create a friendship out of
        # what the caller thinks is a one-way action, so it is surfaced instead
        # and the client offers the accept button.
        if await self.friend_repo.get_pending_request(recipient_id, sender_id) is not None:
            raise IncomingFriendRequestExistsError(
                "This user has already sent you a request — accept it instead"
            )

        request = await self.friend_repo.create_request(sender_id, recipient_id)

        # Denormalised into the payload deliberately. A notification is a
        # snapshot of a moment, and the recipient's client has no endpoint to
        # turn a bare sender_id into a name — without this the toast would read
        # "Friend request" with an empty body.
        sender = await self.user_repo.get_by_id(sender_id)

        # Same unit of work as the insert: a request the recipient is never told
        # about is invisible until they happen to open the friends panel.
        await self.notification_repo.create_many(
            [recipient_id],
            "friend_request",
            {
                "request_id": str(request.id),
                "sender_id": str(sender_id),
                "username": sender.username if sender else None,
            },
        )

        logger.info(
            "friend_request_sent",
            request_id=str(request.id),
            sender_id=str(sender_id),
            recipient_id=str(recipient_id),
        )
        return request
