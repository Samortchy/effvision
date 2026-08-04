from __future__ import annotations
import uuid

from domain.entities.conversation_member import ConversationMember
from domain.exceptions import NotAConversationMemberError
from domain.repositories.conversation_repository import ConversationRepository


class ListConversationMembersUseCase:
    """The roster of a conversation, for the members panel.

    Membership is not public: who you are talking to is as sensitive as what you
    said, so the caller must be an active member themselves — the same check
    GetConversationHistoryUseCase applies before handing back messages.
    """

    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    async def execute(
        self, conversation_id: uuid.UUID, requesting_user_id: uuid.UUID
    ) -> list[ConversationMember]:
        member = await self.conversation_repo.get_member(conversation_id, requesting_user_id)
        if member is None or member.left_at is not None:
            raise NotAConversationMemberError("You are not a member of this conversation")

        # Active members only — someone who left should not linger in the roster.
        return await self.conversation_repo.list_members(conversation_id)
