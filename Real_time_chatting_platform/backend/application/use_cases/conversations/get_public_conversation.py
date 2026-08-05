from domain.repositories.conversation_repository import ConversationRepository
from domain.entities.conversation import Conversation

import structlog

logger = structlog.get_logger()

class GetPublicConversationUseCase:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    async def execute(self) -> Conversation:
        existing = await self.repo.get_public_conversation()

        if existing:
            return existing

        # create_public_conversation, not create(Conversation(...)): the entity
        # has no defaults and its id is the database's to assign, so there is no
        # valid Conversation to hand in here. The repository also resolves the
        # race on the single-public-room index, which a bare insert would not.
        conversation = await self.repo.create_public_conversation("Global chat")
        logger.info("public_conversation_created", conversation_id=str(conversation.id))

        return conversation



