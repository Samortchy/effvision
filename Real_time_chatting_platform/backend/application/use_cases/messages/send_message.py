from __future__ import annotations
import uuid

import structlog

from application.dto.message_dto import MessageRequest, MessageResponse
from application.use_cases.notifications.notify_new_message import NotifyNewMessageUseCase
from domain.repositories.broadcaster import Broadcaster
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.user_repository import UserRepository

logger = structlog.get_logger()


class ConversationNotFound(Exception):
    def __init__(self, convo_id):
        super().__init__(f"The conversation with the ID: {convo_id} wasn't found")


class UserNotFound(Exception):
    def __init__(self, user_id):
        super().__init__(f"The user with the ID: {user_id} wasn't found")


class UserIsNotMember(Exception):
    def __init__(self, convo_id, user_id):
        super().__init__(f"The user with the ID: {user_id} isn't a member in the conversation with the ID: {convo_id}")


class SendMessageUseCase:
    """Persist a message, then fan it out.

    Three things have to happen and the order is not arbitrary:

      1. The message row is written.
      2. Notification rows are written, in the *same* unit of work. If they were
         written afterwards a crash in between would leave a message nobody was
         ever told about, and there is no reconciliation job to catch that.
      3. The live WebSocket broadcast goes last, because it is the only step
         that cannot be rolled back. get_db() commits after this use case
         returns, so a broadcast that ran first would show every connected
         client a message that a failed commit then erased. Sending last does
         not close that window completely — see the note on broadcast() below —
         but it makes it as small as this layering allows.
    """

    def __init__(
        self,
        convo_repo: ConversationRepository,
        message_repo: MessageRepository,
        user_repo: UserRepository,
        notification_repo: NotificationRepository,
        broadcaster: Broadcaster,
    ):
        self.convo_repo = convo_repo
        self.message_repo = message_repo
        self.user_repo = user_repo
        self.notification_repo = notification_repo
        self.broadcaster = broadcaster

    async def execute(
        self, sender_id: uuid.UUID, convo_id: uuid.UUID, data: MessageRequest
    ) -> MessageResponse:
        conversation = await self.convo_repo.get_by_id(convo_id)
        if not conversation:
            raise ConversationNotFound(convo_id)

        user = await self.user_repo.get_by_id(sender_id)
        if not user:
            raise UserNotFound(sender_id)

        member = await self.convo_repo.get_member(convo_id, user.id)
        # `left_at` matters as much as the row existing: someone who left, or an
        # admin removed, still has a membership row and would otherwise keep
        # posting into a room they are no longer in.
        if member is None or member.left_at is not None:
            raise UserIsNotMember(convo_id, user.id)

        message = await self.message_repo.create(convo_id, user.id, data.content)

        # Same transaction as the insert above — a persisted message always has
        # its notifications. The username is passed through rather than looked
        # up again: it is already loaded here, and the notification payload needs
        # it because recipients have no way to resolve a bare sender id.
        await NotifyNewMessageUseCase(self.convo_repo, self.notification_repo).execute(
            message, sender_username=user.username
        )

        response = MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            content=message.content,
            is_edited=message.is_edited,
            edited_at=message.edited_at,
            created_at=message.created_at,
        )

        # exclude the sender: their own client already has this message as the
        # HTTP response, and echoing it back would render it twice.
        await self.broadcaster.broadcast_to_conversation(
            convo_id,
            {"type": "message", "payload": response.model_dump(mode="json")},
            exclude_user_id=sender_id,
        )

        logger.info("message_created", convo_id=str(convo_id), user_id=str(user.id))
        return response
