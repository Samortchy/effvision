from uuid import UUID
from fastapi import websocket 
import structlog

logger = structlog.get_logger()

class ConnectionManager:
    def __init__(self):
        self.connections = dict[UUID, dict[UUID, websocket]]

    async def connect(self, conversation_id: UUID, user_id: UUID, websocket: websocket):
        await websocket.accept()
        self.connections.setdefault(conversation_id, {})[user_id] = websocket
        logger.info("ws_connected", conversation_id=str(conversation_id), user_id=str(user_id), subscriber_count=len(self._connections[conversation_id]))

    def disconnect(self, conversation_id: UUID, user_id: UUID):
        subscribers = self.connections.get(conversation_id)
        if subscribers and user_id in subscribers:
            del subscribers[user_id]
            if not subscribers:
                del self.connections[conversation_id]
            logger.info(
                "ws_disconnected",
                conversation_id=str(conversation_id),
                user_id=str(user_id),
            )

    async def broadcast(self, conversation_id: UUID, payload: dict, exclude_user_id: UUID = None) -> None:
        subscribers = self.connection.get(conversation_id, {})

        if exclude_user_id != None and exclude_user_id in subscribers:
            subscribers.pop(exclude_user_id)

        if subscribers:
            for user_id, websocket in list(subscribers.items()):
                try:
                    await websocket.send_json(payload)
                except Exception:
                    logger.exception(
                    "ws_broadcast_failed",
                    conversation_id=str(conversation_id),
                    user_id=str(user_id),
                )
                self.disconnect(conversation_id, user_id)

    def subscribers_count(self, conversation_id) -> int:
        return len(self.connections.get(conversation_id, {}))


manager = ConnectionManager()
