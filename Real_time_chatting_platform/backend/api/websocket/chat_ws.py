from core.security import decode_token
from infrastructure.websocket.connection_manager import manager
from api.dependencies.repositories import get_conversation_repository
from domain.repositories.conversation_repository import ConversationRepository

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
import structlog
from uuid import UUID

logger = structlog.get_logger()
router = APIRouter()

@router.websocket("/ws/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(...),
    convo_repo: ConversationRepository = Depends(get_conversation_repository),
):
    try:
        payload = decode_token(token, "access")
        user_id = UUID(payload["sub"])
    except Exception:
        logger.warning("ws_auth_failed", conversation_id=str(conversation_id))
        await websocket.close(code=4401)
        return

    is_member = await convo_repo.is_member(conversation_id, user_id)
    if not is_member:
        logger.warning("ws_not_member", conversation_id=str(conversation_id), user_id=str(user_id))
        await websocket.close(code=4403)
        return

    await manager.connect(conversation_id, user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # nothing to do with incoming data yet — next task
    except WebSocketDisconnect:
        manager.disconnect(conversation_id, user_id)