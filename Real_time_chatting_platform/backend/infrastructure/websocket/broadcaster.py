from __future__ import annotations
from typing import Any
import uuid

from domain.repositories.broadcaster import Broadcaster

# ASSUMPTION: Ahmed's connection manager (Day 4 Task 3) exposes a method
# `broadcast_to_conversation(conversation_id, message: dict)`.
# Once his real file exists, verify this import path and method signature
# match, and adjust if they don't.
from infrastructure.websocket.connection_manager import ConnectionManager


class WebSocketBroadcaster(Broadcaster):
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def broadcast_to_conversation(self, conversation_id: uuid.UUID, event: dict[str, Any]) -> None:
        await self.connection_manager.broadcast(conversation_id, event)