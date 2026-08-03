from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.message_read_status import MessageReadStatusEntity

class MessageReadStatusRepository(ABC):
    @abstractmethod
    async def bulk_create(self, statuses: List[MessageReadStatusEntity]) -> None:
        ...

    @abstractmethod
    async def mark_as_read(self, message_id, user_id) -> Optional[MessageReadStatusEntity]:
        ...

    @abstractmethod
    async def count_unread(self, conversation_id, user_id) -> int:
        ...