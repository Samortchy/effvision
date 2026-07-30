from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import uuid


class Broadcaster(ABC):
    """Port for real-time event delivery. Concrete implementation wraps the
    actual WebSocket connection manager (infrastructure/websocket)."""

    @abstractmethod
    async def broadcast_to_conversation(self, conversation_id: uuid.UUID, event: dict[str, Any]) -> None:
        ...