from __future__ import annotations
from typing import Any
import uuid

from domain.repositories.broadcaster import Broadcaster
from infrastructure.websocket.connection_manager import ConnectionManager, manager


class WebSocketBroadcaster(Broadcaster):
    """Adapter binding the Broadcaster port to the in-process ConnectionManager."""

    def __init__(self, connection_manager: ConnectionManager | None = None):
        # Defaults to the process-wide manager the WebSocket route registers
        # against; injectable so tests can pass a double.
        self.connection_manager = connection_manager or manager

    async def broadcast_to_conversation(
        self,
        conversation_id: uuid.UUID,
        event: dict[str, Any],
        exclude_user_id: uuid.UUID | None = None,
    ) -> None:
        await self.connection_manager.broadcast(
            conversation_id, event, exclude_user_id=exclude_user_id
        )
