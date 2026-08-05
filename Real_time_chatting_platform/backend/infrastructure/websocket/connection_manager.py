from uuid import UUID

from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """In-process registry of live WebSocket connections, keyed by conversation.

    Single-process only: the registry is a plain dict, so two uvicorn workers
    each hold half the room and neither can reach the other's subscribers.
    Moving to more than one worker means putting a Redis pub/sub (or similar)
    behind this class.
    """

    def __init__(self) -> None:
        # conversation_id -> {user_id -> socket}
        self.connections: dict[UUID, dict[UUID, WebSocket]] = {}

    async def connect(self, conversation_id: UUID, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(conversation_id, {})[user_id] = websocket
        logger.info(
            "ws_connected",
            conversation_id=str(conversation_id),
            user_id=str(user_id),
            subscriber_count=len(self.connections[conversation_id]),
        )

    def disconnect(self, conversation_id: UUID, user_id: UUID) -> None:
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

    async def broadcast(
        self, conversation_id: UUID, payload: dict, exclude_user_id: UUID | None = None
    ) -> None:
        # Snapshot before iterating: a failed send calls disconnect(), which
        # mutates the live dict. Excluding the sender is also done on the copy —
        # popping it from the registry would drop their connection for good.
        subscribers = list(self.connections.get(conversation_id, {}).items())

        for user_id, websocket in subscribers:
            if exclude_user_id is not None and user_id == exclude_user_id:
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                # A dead socket is expected (tab closed, network dropped) and
                # must not stop delivery to everyone else in the room.
                logger.exception(
                    "ws_broadcast_failed",
                    conversation_id=str(conversation_id),
                    user_id=str(user_id),
                )
                self.disconnect(conversation_id, user_id)

    def subscribers_count(self, conversation_id: UUID) -> int:
        return len(self.connections.get(conversation_id, {}))


manager = ConnectionManager()
