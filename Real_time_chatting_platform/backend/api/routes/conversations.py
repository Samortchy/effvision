from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import (
    get_conversation_repository,
    get_message_repository,
    get_user_repository,
)
from application.dto.conversation_dto import (
    AddMemberRequest,
    ChangeMemberRoleRequest,
    ConversationMemberResponse,
    ConversationResponse,
    CreateGroupRequest,
    MessageHistoryQuery,
    MessageResponse,
    StartPrivateConversationRequest,
)
from application.dto.user_dto import UserSummary
from application.use_cases.conversations.add_conversation_member import AddConversationMemberUseCase
from application.use_cases.conversations.create_group_conversation import CreateGroupConversationUseCase
from application.use_cases.conversations.get_conversation_history import GetConversationHistoryUseCase
from application.use_cases.conversations.leave_group import LeaveGroupUseCase
from application.use_cases.conversations.manage_membership import ChangeMemberRoleUseCase, RemoveMemberUseCase
from application.use_cases.conversations.join_public_conversation import (
    AlreadyAMemberError,
    JoinPublicConversationUseCase,
    PublicConvoNotFound,
    UserNotFound,
)
from application.use_cases.conversations.start_private_conversation import StartPrivateConversationUseCase
from application.use_cases.conversations.get_public_conversation import GetPublicConversationUseCase
from application.use_cases.conversations.list_conversation_members import ListConversationMembersUseCase
from application.use_cases.conversations.list_user_conversations import ListUserConversationsUseCase
from domain.entities.user import User
from domain.exceptions import (
    AlreadyAConversationMemberError,
    CannotAddMembersError,
    CannotLeavePrivateConversationError,
    CannotMessageSelfError,
    ConversationNotFoundError,
    InsufficientPermissionError,
    LastOwnerError,
    MemberNotFoundError,
    NotAConversationMemberError,
    UserNotFoundError,
)
from domain.repositories.conversation_repository import ConversationRepository
from domain.repositories.message_repository import MessageRepository
from domain.repositories.user_repository import UserRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_my_conversations(
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> list[ConversationResponse]:
    """Every conversation the caller is an active member of, newest first.

    Private conversations carry `peer` — the other participant — because they
    have no server-side name and the client would otherwise have nothing to
    render as a title.
    """
    use_case = ListUserConversationsUseCase(conversation_repo)
    items = await use_case.execute(current_user.id)

    responses = []
    for item in items:
        response = ConversationResponse.model_validate(item.conversation)
        # UserSummary, not the User entity: it exposes id/username/display_name/
        # avatar_url/status and nothing else, so password_hash and email cannot
        # ride along into a list every member of the room can fetch.
        response.peer = UserSummary.model_validate(item.peer) if item.peer else None
        responses.append(response)
    return responses


@router.post("/private", response_model=ConversationResponse)
async def start_private_conversation(
    payload: StartPrivateConversationRequest,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ConversationResponse:
    use_case = StartPrivateConversationUseCase(conversation_repo, user_repo)
    try:
        conversation = await use_case.execute(current_user.id, payload.recipient_id)
    except CannotMessageSelfError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ConversationResponse.model_validate(conversation)


@router.post("/group", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_group_conversation(
    payload: CreateGroupRequest,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ConversationResponse:
    """Create a group. The caller becomes its owner."""
    use_case = CreateGroupConversationUseCase(conversation_repo, user_repo)
    try:
        conversation = await use_case.execute(
            creator_id=current_user.id,
            name=payload.name,
            description=payload.description,
            member_ids=payload.member_ids,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ConversationResponse.model_validate(conversation)


@router.post(
    "/{conversation_id}/members",
    response_model=ConversationMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_conversation_member(
    conversation_id: uuid.UUID,
    payload: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ConversationMemberResponse:
    """Add a user to a group. Owners and admins only."""
    use_case = AddConversationMemberUseCase(conversation_repo, user_repo)
    try:
        member = await use_case.execute(
            conversation_id=conversation_id,
            actor_user_id=current_user.id,
            target_user_id=payload.user_id,
            role=payload.role,
        )
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CannotAddMembersError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AlreadyAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return ConversationMemberResponse.model_validate(member)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_history(
    conversation_id: uuid.UUID,
    query: MessageHistoryQuery = Depends(),
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
) -> list[MessageResponse]:
    use_case = GetConversationHistoryUseCase(conversation_repo, message_repo)
    try:
        messages = await use_case.execute(conversation_id, current_user.id, query.before, query.limit)
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return [MessageResponse.model_validate(m) for m in messages]


# response_model=None is required alongside the `-> None` annotation: FastAPI
# would otherwise infer NoneType as a response body, which 204 forbids.
@router.post("/{conversation_id}/leave", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def leave_group(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> None:
    use_case = LeaveGroupUseCase(conversation_repo)
    try:
        await use_case.execute(conversation_id, current_user.id)
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CannotLeavePrivateConversationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except LastOwnerError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch(
    "/{conversation_id}/members/{target_user_id}/role",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def change_member_role(
    conversation_id: uuid.UUID,
    target_user_id: uuid.UUID,
    payload: ChangeMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> None:
    use_case = ChangeMemberRoleUseCase(conversation_repo)
    try:
        await use_case.execute(conversation_id, current_user.id, target_user_id, payload.role)
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except MemberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except LastOwnerError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/{conversation_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_member(
    conversation_id: uuid.UUID,
    target_user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> None:
    use_case = RemoveMemberUseCase(conversation_repo)
    try:
        await use_case.execute(conversation_id, current_user.id, target_user_id)
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except MemberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/public", response_model=ConversationResponse)
async def get_public_conversation(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    use_case = GetPublicConversationUseCase(conversation_repo)
    conversation = await use_case.execute()
    return ConversationResponse.model_validate(conversation)


# POST, not GET: this inserts a membership row. A GET that mutates state can be
# prefetched by the browser, retried by a proxy, or cached — any of which joins
# the user to the room without them asking.
@router.post("/public/join", response_model=ConversationMemberResponse, status_code=201)
async def join_public_conversation(current_user: User = Depends(get_current_user),
                                    convo_repo: ConversationRepository = Depends(get_conversation_repository),
                                    user_repo: UserRepository = Depends(get_user_repository)) -> ConversationMemberResponse:
    use_case = JoinPublicConversationUseCase(user_repo, convo_repo)
    try:
        member = await use_case.execute(current_user.id)
    except PublicConvoNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AlreadyAMemberError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return ConversationMemberResponse.model_validate(member)


@router.get("/{conversation_id}/members", response_model=list[ConversationMemberResponse])
async def list_conversation_members(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> list[ConversationMemberResponse]:
    use_case = ListConversationMembersUseCase(conversation_repo)
    try:
        members = await use_case.execute(conversation_id, current_user.id)
    except NotAConversationMemberError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return [ConversationMemberResponse.model_validate(m) for m in members]
