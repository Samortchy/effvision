from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import get_conversation_repository, get_message_repository
from application.dto.conversation_dto import MessageResponse
from application.dto.message_dto import MessageSearchQuery
from application.use_cases.messages.delete_message import DeleteMessageUseCase
from application.use_cases.messages.search_messages import SearchMessagesUseCase
from domain.entities.user import User
from domain.exceptions import MessageNotFoundError, NotAConversationMemberError, NotMessageOwnerError
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository

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