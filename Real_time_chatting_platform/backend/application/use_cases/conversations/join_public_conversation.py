from domain.entities.conversation_member import ConversationMember
from domain.repositories.user_repository import UserRepository
from domain.repositories.conversation_repository import ConversationRepository

from uuid import UUID
import structlog

logger = structlog.get_logger()

class PublicConvoNotFound(Exception):
    def __init__(self):
        super().__init__("public conversation not found")

class UserNotFound(Exception):
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found")

class AlreadyAMemberError(Exception):
    """Named for what it means here — the user is already in the room.

    Deliberately not `IntegrityError`: that name is sqlalchemy.exc.IntegrityError
    throughout the persistence layer, and a second class under the same name in
    the application layer makes every `except IntegrityError` ambiguous to read
    and easy to bind to the wrong one.
    """

    def __init__(self, user_id: str, convo_id: str):
        super().__init__(f"User with ID {user_id} already joined this conversation with ID {convo_id}")

class JoinPublicConversationUseCase:
    def __init__(self, user_repo: UserRepository, convo_repo: ConversationRepository):
        self.user_repo = user_repo
        self.convo_repo = convo_repo
    
    async def execute(self, user_id: UUID) -> ConversationMember:
        existing_convo = await self.convo_repo.get_public_conversation()

        if not existing_convo:
            raise PublicConvoNotFound()

        user =  await self.user_repo.get_by_id(user_id)

        if not user:
            raise UserNotFound(str(user_id))
        
        logger.info("user_fetched", user_id = str(user_id))


        membership = await self.convo_repo.get_member(existing_convo.id, user.id)

        # get_member returns the row even for someone who *left* — it is
        # left_at, not the row's existence, that decides current membership.
        # Testing the row alone locked anyone who ever left the public room out
        # of it permanently.
        if membership is not None and membership.left_at is None:
            raise AlreadyAMemberError(str(user.id), str(existing_convo.id))

        if membership is not None:
            # Rejoining. uq_conversation_member forbids a second row for the
            # same pair, so the original one has to be revived.
            joining = await self.convo_repo.reinstate_member(existing_convo.id, user.id, "member")
        else:
            # Returns the created membership row — the route serialises it, so
            # this must not be the repository's old `None`.
            joining = await self.convo_repo.add_member(existing_convo.id, user.id)

        logger.info(
            "user_joined_public_convo",
            convo_id=str(existing_convo.id),
            user_id=str(user.id),
            rejoined=membership is not None,
        )
        return joining


