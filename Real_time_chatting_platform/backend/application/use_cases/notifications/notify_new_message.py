from __future__ import annotations
import uuid

from domain.entities.message import Message
from domain.entities.notification import Notification
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.notification_repository import NotificationRepository


class NotifyNewMessageUseCase:
    """Produces the `new_message` notifications that /notifications/stream consumes.

    Call this from the send-message path (Day 4 Task 1) after the message row is
    written and in the same unit of work, so a message is never persisted without
    its notifications:

        await NotifyNewMessageUseCase(conversation_repo, notification_repo).execute(message)
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        notification_repo: NotificationRepository,
    ):
        self.conversation_repo = conversation_repo
        self.notification_repo = notification_repo

    async def execute(
        self, message: Message, sender_username: str | None = None
    ) -> list[Notification]:
        members = await self.conversation_repo.list_members(message.conversation_id)
        recipient_ids: list[uuid.UUID] = [
            member.user_id
            for member in members
            if member.user_id != message.sender_id and not member.muted
        ]

        return await self.notification_repo.create_many(
            recipient_ids,
            "new_message",
            {
                "message_id": str(message.id),
                "conversation_id": str(message.conversation_id),
                # None for a system-authored message (sender_id is nullable).
                "sender_id": str(message.sender_id) if message.sender_id else None,
                # Denormalised alongside the id: the recipient's client has no
                # endpoint that turns a user id into a name, so without this the
                # toast reads "New message" with nobody attached. A notification
                # is a snapshot of a moment, so a later rename not being
                # reflected here is correct, not stale.
                "sender_username": sender_username,
                # Enough for a toast/preview without a second round-trip. Trimmed
                # so a long message doesn't bloat every recipient's payload.
                "preview": message.content[:140],
            },
        )
