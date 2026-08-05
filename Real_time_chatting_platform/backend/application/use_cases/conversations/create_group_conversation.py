from __future__ import annotations
from collections.abc import Sequence
import uuid

import structlog

from domain.entities.conversation import Conversation
from domain.exceptions import UserNotFoundError
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.user_repository import UserRepository

logger = structlog.get_logger()


class CreateGroupConversationUseCase:
    """Create a group and seed its membership.

    The creator always becomes owner. That is not a courtesy — LeaveGroupUseCase
    and ChangeMemberRoleUseCase both refuse to leave a group without one, so a
    group created without an owner would be permanently unadministrable.
    """

    def __init__(self, conversation_repo: ConversationRepository, user_repo: UserRepository):
        self.conversation_repo = conversation_repo
        self.user_repo = user_repo

    async def execute(
        self,
        creator_id: uuid.UUID,
        name: str,
        description: str | None = None,
        member_ids: Sequence[uuid.UUID] = (),
    ) -> Conversation:
        # Dedupe, and drop the creator if they listed themselves — they are
        # added below as owner, and a second row for the same pair would violate
        # uq_conversation_member.
        invitees = {uid for uid in member_ids if uid != creator_id}

        # Validated up front, before anything is written: without this a bad id
        # fails on the users foreign key mid-way, leaving a half-populated group
        # and surfacing as a 500 rather than a 404.
        for user_id in invitees:
            if await self.user_repo.get_by_id(user_id) is None:
                raise UserNotFoundError(f"User {user_id} does not exist")

        conversation = await self.conversation_repo.create_group_conversation(
            name=name, description=description, created_by=creator_id
        )

        await self.conversation_repo.add_member(conversation.id, creator_id, "owner")
        for user_id in invitees:
            await self.conversation_repo.add_member(conversation.id, user_id, "member")

        logger.info(
            "group_created",
            conversation_id=str(conversation.id),
            created_by=str(creator_id),
            member_count=len(invitees) + 1,
        )
        return conversation
