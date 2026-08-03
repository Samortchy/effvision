from domain.repositories.message_repository import MessageRepository
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.user_repository import UserRepository

from application.dto.message_dto import MessageRequest, MessageResponse

import structlog

logger = structlog.get_logger()

class ConversationNotFound(Exception):
    def __init__(self, convo_id):
        super().__init__(f"The conversation with the ID: {convo_id} wasn't found")

class UserNotFound(Exception):
    def __init__(self, user_id):
        super().__init__(f"The user with the ID: {user_id} wasn't found")

class UserIsNotMember(Exception):
    def __init__(self, convo_id, user_id):
        super().__init__(f"The user with the ID: {user_id} isn't a member in the conversation with the ID: {convo_id}")


class SendMessageUseCase:
    def __init__(self, convo_repo: ConversationRepository, message_repo: MessageRepository, user_repo: UserRepository):
        self.convo_repo = convo_repo
        self.message_repo = message_repo
        self.user_repo = user_repo

    async def execute(self, sender_id, convo_id, data: MessageRequest) -> MessageResponse:
        conversation = await self.convo_repo.get_by_id(convo_id)

        if not conversation:
            raise ConversationNotFound(convo_id)

        user = await self.user_repo.get_by_id(sender_id)

        if not user:
            raise UserNotFound(sender_id)

        is_member = await self.convo_repo.get_member(convo_id, user.id)

        if not is_member:
            raise UserIsNotMember(convo_id, user.id)

        message = await self.message_repo.create(convo_id, user.id, data.content)

        logger.info("message created successfuly", convo_id = convo_id, user_id = user.id)
        return MessageResponse(message.id, 
                               message.conversation_id, 
                               message.sender_id, message.content, 
                               message.is_edited, message.edited_at, 
                               message.created_at)

