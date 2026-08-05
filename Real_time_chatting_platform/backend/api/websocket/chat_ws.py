import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.dependencies.repositories import open_conversation_repository
from application.use_cases.messages.typing_indicator import TypingIndicatorUseCase
from core.security import decode_token
from domain.exceptions import NotAConversationMemberError
from infrastructure.websocket.broadcaster import WebSocketBroadcaster
from infrastructure.websocket.connection_manager import manager

logger = structlog.get_logger()
router = APIRouter()

# Close codes. 4000-4999 is the range reserved for application use; the browser
# receives these verbatim on the CloseEvent, so the client can tell "your token
# expired" apart from "you are not in this room".
WS_UNAUTHORIZED = 4401
WS_FORBIDDEN = 4403

_TYPING_EVENTS = {"typing_start": True, "typing_stop": False}


@router.websocket("/ws/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(...),
):
    # No Depends(get_conversation_repository) here: FastAPI would hold that
    # session open for the entire life of the socket. Each DB touch below opens
    # its own short-lived unit of work instead.
    try:
        payload = decode_token(token, "access")
        user_id = UUID(payload["sub"])
    except Exception:
        logger.warning("ws_auth_failed", conversation_id=str(conversation_id))
        await websocket.close(code=WS_UNAUTHORIZED)
        return

    async with open_conversation_repository() as convo_repo:
        is_member = await convo_repo.is_member(conversation_id, user_id)

    if not is_member:
        logger.warning("ws_not_member", conversation_id=str(conversation_id), user_id=str(user_id))
        await websocket.close(code=WS_FORBIDDEN)
        return

    await manager.connect(conversation_id, user_id, websocket)
    broadcaster = WebSocketBroadcaster()

    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_frame(websocket, broadcaster, conversation_id, user_id, raw)
    except WebSocketDisconnect:
        pass
    except Exception:
        # Any other error (socket torn down mid-receive, task cancelled during
        # shutdown) must still reach the finally below — otherwise the entry
        # stays in the registry forever and the room leaks a dead socket.
        logger.exception(
            "ws_receive_failed",
            conversation_id=str(conversation_id),
            user_id=str(user_id),
        )
        raise
    finally:
        manager.disconnect(conversation_id, user_id)


async def _handle_frame(
    websocket: WebSocket,
    broadcaster: WebSocketBroadcaster,
    conversation_id: UUID,
    user_id: UUID,
    raw: str,
) -> None:
    """Dispatch one inbound frame.

    Nothing in here may raise: a malformed frame from one client must not tear
    down that client's socket, let alone affect anyone else in the room. Bad
    input gets an error frame back and the loop continues.
    """
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        await _send_error(websocket, "malformed_frame", "Frame is not valid JSON")
        return

    if not isinstance(envelope, dict):
        await _send_error(websocket, "malformed_frame", "Frame must be a JSON object")
        return

    event_type = envelope.get("type")

    if event_type in _TYPING_EVENTS:
        # Re-checked per frame rather than trusted from the handshake: a member
        # removed mid-session still holds an open socket, and this is where that
        # is caught.
        async with open_conversation_repository() as convo_repo:
            use_case = TypingIndicatorUseCase(convo_repo, broadcaster)
            try:
                await use_case.execute(conversation_id, user_id, _TYPING_EVENTS[event_type])
            except NotAConversationMemberError:
                await _send_error(websocket, "forbidden", "You are not a member of this conversation")
        return

    await _send_error(websocket, "unknown_type", f"Unsupported frame type: {event_type!r}")


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    try:
        await websocket.send_json({"type": "error", "code": code, "message": message})
    except Exception:
        # The socket is already gone; the receive loop will notice next tick.
        logger.debug("ws_error_send_failed", code=code)
