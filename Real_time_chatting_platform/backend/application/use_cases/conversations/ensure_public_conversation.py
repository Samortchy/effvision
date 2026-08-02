from domain.entities.conversation import Conversation
from domain.repositories.conversation_repository import ConversationRepository

import structlog

logger = structlog.get_logger()

class EnsurePublicConversationUseCase:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    async def execute(self) -> Conversation:
        existing = await self.repo.get_public_conversation()

        if existing:
            return existing

        created = await self.repo.create_public_conversation("Global chat")
        logger.info("public_conversation_created", conversation_id=str(created.id))

        return created
