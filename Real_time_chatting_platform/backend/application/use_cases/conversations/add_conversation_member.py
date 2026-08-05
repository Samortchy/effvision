from __future__ import annotations
import uuid

import structlog

from domain.entities.conversation_member import ConversationMember, Role
from domain.exceptions import (
    AlreadyAConversationMemberError,
    CannotAddMembersError,
    ConversationNotFoundError,
    NotAConversationMemberError,
    UserNotFoundError,
)
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.user_repository import UserRepository
from domain.services.membership_service import MembershipService

logger = structlog.get_logger()


class AddConversationMemberUseCase:
    """Invite a user into a group.

    Order matters: conversation type, then the actor's standing, then their
    permission, then the target. Checking the target first would let anyone
    probe which user ids exist by watching whether they got a 404 or a 403.
    """

    def __init__(self, conversation_repo: ConversationRepository, user_repo: UserRepository):
        self.conversation_repo = conversation_repo
        self.user_repo = user_repo

    async def execute(
        self,
        conversation_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: Role = "member",
    ) -> ConversationMember:
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError("Conversation not found")

        if conversation.type == "private":
            raise CannotAddMembersError(
                "A private conversation is between exactly two people — create a group instead"
            )
        if conversation.type == "public":
            raise CannotAddMembersError(
                "Anyone can join the public room themselves; nobody needs adding to it"
            )

        actor = await self.conversation_repo.get_member(conversation_id, actor_user_id)
        if actor is None or actor.left_at is not None:
            raise NotAConversationMemberError("You are not a member of this conversation")

        MembershipService.assert_can_add_member(actor.role)

        if await self.user_repo.get_by_id(target_user_id) is None:
            raise UserNotFoundError("That user does not exist")

        existing = await self.conversation_repo.get_member(conversation_id, target_user_id)
        if existing is not None:
            if existing.left_at is None:
                raise AlreadyAConversationMemberError("That user is already in this conversation")
            # They left before. The row is still there and the unique constraint
            # forbids a second one, so revive it rather than inserting.
            member = await self.conversation_repo.reinstate_member(
                conversation_id, target_user_id, role
            )
        else:
            member = await self.conversation_repo.add_member(
                conversation_id, target_user_id, role
            )

        logger.info(
            "member_added",
            conversation_id=str(conversation_id),
            actor_id=str(actor_user_id),
            target_id=str(target_user_id),
            reinstated=existing is not None,
        )
        return member
