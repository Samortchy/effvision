from __future__ import annotations
from datetime import datetime, timezone
import uuid

from domain.exceptions import (
    CannotLeavePrivateConversationError,
    ConversationNotFoundError,
    LastOwnerError,
    NotAConversationMemberError,
)
from domain.repositories.conversation_repository import ConversationRepository


class LeaveGroupUseCase:
    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    async def execute(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError("Conversation not found")

        # A 1:1 conversation has no "leaving" — both parties are permanent
        # members. Allowing it would strand the other user's history and let a
        # second private conversation be created for the same pair.
        if conversation.type == "private":
            raise CannotLeavePrivateConversationError("You cannot leave a private conversation")

        member = await self.conversation_repo.get_member(conversation_id, user_id)
        if member is None or member.left_at is not None:
            raise NotAConversationMemberError("You are not a member of this conversation")

        if member.role == "owner":
            await self._assert_can_owner_leave(conversation_id, user_id)

        await self.conversation_repo.mark_member_left(conversation_id, user_id, datetime.now(timezone.utc))

    async def _assert_can_owner_leave(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """An owner may only leave if someone else can still administer the
        conversation, or if they are the last member standing."""
        members = await self.conversation_repo.list_members(conversation_id)
        others = [m for m in members if m.user_id != user_id]
        if not others:
            return
        if not any(m.role == "owner" for m in others):
            raise LastOwnerError(
                "Transfer ownership to another member before leaving this conversation"
            )
