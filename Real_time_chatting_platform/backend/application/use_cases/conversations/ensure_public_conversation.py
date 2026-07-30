from domain.repositories.conversation_repository import ConversationRepository
from domain.entities.conversations import Conversation

import structlog

logger = structlog.get_logger()

class EnsurePublicConversationUseCase:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    async def execute(self) -> Conversation:
        exisits = await self.repo.get_public_conversation()

        if exisits:
            return exisits

        create = await self.repo.create(Conversation(id = None, type = "public", name = "Global chat"))
        logger.info("public_conversation_created", conversation_id=str(create.id))

        return create

        
