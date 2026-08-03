from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class MessageReadStatusEntity:
    id: Optional[UUID]
    message_id: UUID
    user_id: UUID
    read_at: Optional[datetime] = None