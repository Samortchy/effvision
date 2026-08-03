from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from domain.repositories.conversation_repository import ConversationRepository
from domain.entities.conversations import Conversation
from infrastructure.database.models import Conversation as ConversationModel, ConversationMember as MemberModel


class SQLAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_public_conversation(self):
        result = await self.session.execute(
            select(ConversationORM).where(
                ConversationORM.type == "public"
            )
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None


    async def create(self, conversation: Conversation) -> Conversation:
        row = ConversationModel(type=conversation.type, name=conversation.name)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)
    

    async def add_member(self, conversation_id, user_id, role: str = "member") -> None:
        self._session.add(MemberModel(conversation_id=conversation_id, user_id=user_id, role=role))
        await self._session.commit()

    async def is_member(self, conversation_id, user_id) -> bool:
        result = await self._session.execute(
            select(MemberModel).where(
                MemberModel.conversation_id == conversation_id,
                MemberModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    def _to_entity(self, row: ConversationModel) -> Conversation:
        return Conversation(
            id=row.id, type=row.type, name=row.name,
            description=row.description, created_by=row.created_by, created_at=row.created_at,
        )
