from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Literal


@dataclass
class Conversation:
    id: UUID
    type: Literal['public', 'private', 'group']
    name: str = None
    description: str = None
    created_by: UUID = None
    created_at: datetime = None