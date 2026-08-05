from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import (
    get_broadcaster,
    get_conversation_repository,
    get_message_repository,
    get_notification_repository,
    get_user_repository,
)

from application.dto.conversation_dto import MessageResponse
from application.dto.message_dto import EditMessageRequest, MessageRequest, MessageSearchQuery

from application.use_cases.messages.delete_message import DeleteMessageUseCase
from application.use_cases.messages.edit_message import EditMessageUseCase
from application.use_cases.messages.search_messages import SearchMessagesUseCase
from application.use_cases.messages.send_message import (
    ConversationNotFound,
    SendMessageUseCase,
    UserIsNotMember,
)

from domain.entities.user import User
# One canonical definition per error. These used to be imported twice — once
# from edit_message, once from here — and the second import silently rebound the
# names, so the `except` clauses below never matched what the use case raised.
from domain.exceptions import (
    MessageNotFoundError,
    NotAConversationMemberError,
    NotMessageOwnerError,
)

from domain.repositories.broadcaster import Broadcaster
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.user_repository import UserRepository


router = APIRouter(prefix="/messages", tags=["messages"])


# response_model=None is required alongside the `-> None` annotation: FastAPI
# would otherwise infer NoneType as a response body, which 204 forbids.
@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    message_repo: MessageRepository = Depends(get_message_repository),
) -> None:
    use_case = DeleteMessageUseCase(message_repo)
    try:
        await use_case.execute(message_id, current_user.id)
    except MessageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotMessageOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{conversation_id}/search", response_model=list[MessageResponse])
async def search_messages(
    conversation_id: uuid.UUID,
    query: MessageSearchQuery = Depends(),
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
) -> list[MessageResponse]:
    use_case = SearchMessagesUseCase(conversation_repo, message_repo)
    try:
        messages = await use_case.execute(conversation_id, current_user.id, query.q, query.limit, query.offset)
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return [MessageResponse.model_validate(m) for m in messages]


# POST /messages/{conversation_id} — the trailing "/messages" segment this route
# used to carry made the full path /messages/{id}/messages.
@router.post("/{conversation_id}", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageRequest,
    current_user: User = Depends(get_current_user),
    message_repo: MessageRepository = Depends(get_message_repository),
    convo_repo: ConversationRepository = Depends(get_conversation_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    broadcaster: Broadcaster = Depends(get_broadcaster),
):
    # Keyword arguments throughout: both the constructor and execute() take
    # same-typed parameters in an order that is easy to transpose silently.
    use_case = SendMessageUseCase(
        convo_repo=convo_repo,
        message_repo=message_repo,
        user_repo=user_repo,
        notification_repo=notification_repo,
        broadcaster=broadcaster,
    )
    try:
        return await use_case.execute(
            sender_id=current_user.id,
            convo_id=conversation_id,
            data=data,
        )
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except UserIsNotMember:
        raise HTTPException(status_code=403, detail="You are not a member of this conversation")


# PATCH /messages/{message_id} — was /messages/messages/{message_id}.
@router.patch("/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: uuid.UUID,
    data: EditMessageRequest,
    current_user: User = Depends(get_current_user),
    message_repo: MessageRepository = Depends(get_message_repository),
):
    use_case = EditMessageUseCase(message_repo)
    try:
        return await use_case.execute(message_id, current_user.id, data)
    except MessageNotFoundError:
        raise HTTPException(status_code=404, detail="Message not found")
    except NotMessageOwnerError:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")
