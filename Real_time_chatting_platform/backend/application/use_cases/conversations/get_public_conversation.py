from domain.repositories.conversation_repository import ConversationRepository
from domain.entities.conversation import Conversation

import structlog

logger = structlog.get_logger()

class GetPublicConversationUseCase:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    async def execute(self) -> Conversation:
        exisits = await self.repo.get_public_conversation()

        if exisits:
            return exisits

        conversation = await self.repo.create(Conversation(id = None, type = "public", name = "Global chat"))
        logger.info("public_conversation_created", conversation_id=str(conversation.id))

        return conversation



