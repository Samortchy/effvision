from __future__ import annotations
from datetime import datetime, timezone
import uuid

from domain.entities.conversation_member import Role
from domain.exceptions import (
    LastOwnerError,
    MemberNotFoundError,
    NotAConversationMemberError,
)
from domain.repositories.conversation_repository import ConversationRepository
from domain.services.membership_service import MembershipService


async def _load_actor_and_target(
    conversation_repo: ConversationRepository,
    conversation_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
):
    actor = await conversation_repo.get_member(conversation_id, actor_user_id)
    if actor is None or actor.left_at is not None:
        raise NotAConversationMemberError("You are not a member of this conversation")

    target = await conversation_repo.get_member(conversation_id, target_user_id)
    if target is None or target.left_at is not None:
        raise MemberNotFoundError("Target user is not a member of this conversation")

    return actor, target


class ChangeMemberRoleUseCase:
    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    async def execute(
        self, conversation_id: uuid.UUID, actor_user_id: uuid.UUID, target_user_id: uuid.UUID, new_role: Role
    ) -> None:
        actor, target = await _load_actor_and_target(
            self.conversation_repo, conversation_id, actor_user_id, target_user_id
        )

        MembershipService.assert_can_change_role(actor.role, target.role, new_role)

        if target.role == "owner" and new_role != "owner":
            await self._assert_not_last_owner(conversation_id)

        await self.conversation_repo.update_member_role(conversation_id, target_user_id, new_role)

    async def _assert_not_last_owner(self, conversation_id: uuid.UUID) -> None:
        members = await self.conversation_repo.list_members(conversation_id)
        if sum(1 for m in members if m.role == "owner") <= 1:
            raise LastOwnerError(
                "Cannot demote the last owner - promote another member to owner first"
            )


class RemoveMemberUseCase:
    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    async def execute(self, conversation_id: uuid.UUID, actor_user_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
        actor, target = await _load_actor_and_target(
            self.conversation_repo, conversation_id, actor_user_id, target_user_id
        )

        MembershipService.assert_can_remove_member(actor.role, target.role)

        await self.conversation_repo.mark_member_left(conversation_id, target_user_id, datetime.now(timezone.utc))
