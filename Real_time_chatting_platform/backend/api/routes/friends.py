from __future__ import annotations
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import (
    get_friend_repository,
    get_notification_repository,
    get_user_repository,
)
from application.dto.friend_dto import FriendRequestResponse, SendFriendRequestRequest
from application.dto.user_dto import UserSummary
from application.use_cases.friends.manage_friends import (
    ListFriendRequestsUseCase,
    ListFriendsUseCase,
    RemoveFriendUseCase,
)
from application.use_cases.friends.respond_to_friend_request import RespondToFriendRequestUseCase
from application.use_cases.friends.send_friend_request import SendFriendRequestUseCase
from domain.entities.user import User
from domain.exceptions import (
    AlreadyFriendsError,
    CannotFriendSelfError,
    FriendRequestAlreadyAnsweredError,
    FriendRequestAlreadySentError,
    FriendRequestNotFoundError,
    IncomingFriendRequestExistsError,
    NotFriendRequestRecipientError,
    NotFriendsError,
    UserNotFoundError,
)
from domain.repositories.friend_repository import FriendRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.user_repository import UserRepository

router = APIRouter(prefix="/friends", tags=["friends"])


def _to_request_response(request, user: User) -> FriendRequestResponse:
    return FriendRequestResponse(
        id=request.id,
        sender_id=request.sender_id,
        recipient_id=request.recipient_id,
        status=request.status,
        created_at=request.created_at,
        responded_at=request.responded_at,
        # UserSummary, so password_hash and email never ride along.
        user=UserSummary.model_validate(user),
    )


@router.get("", response_model=list[UserSummary])
async def list_friends(
    current_user: User = Depends(get_current_user),
    friend_repo: FriendRepository = Depends(get_friend_repository),
) -> list[UserSummary]:
    """Everyone the caller is friends with, alphabetically."""
    friends = await ListFriendsUseCase(friend_repo).execute(current_user.id)
    return [UserSummary.model_validate(f) for f in friends]


# Declared before /requests/{request_id}/... so the literal path is matched
# first — though FastAPI would not confuse them here, the ordering keeps the
# intent obvious to the next reader.
@router.get("/requests", response_model=list[FriendRequestResponse])
async def list_friend_requests(
    direction: Literal["incoming", "outgoing"] = Query(
        default="incoming",
        description="incoming = sent to you; outgoing = sent by you. Pending only.",
    ),
    current_user: User = Depends(get_current_user),
    friend_repo: FriendRepository = Depends(get_friend_repository),
) -> list[FriendRequestResponse]:
    pairs = await ListFriendRequestsUseCase(friend_repo).execute(current_user.id, direction)
    return [_to_request_response(req, user) for req, user in pairs]


@router.post("/requests", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    payload: SendFriendRequestRequest,
    current_user: User = Depends(get_current_user),
    friend_repo: FriendRepository = Depends(get_friend_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> FriendRequestResponse:
    use_case = SendFriendRequestUseCase(friend_repo, user_repo, notification_repo)
    try:
        request = await use_case.execute(current_user.id, payload.user_id)
    except CannotFriendSelfError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (
        AlreadyFriendsError,
        FriendRequestAlreadySentError,
        IncomingFriendRequestExistsError,
    ) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    recipient = await user_repo.get_by_id(payload.user_id)
    return _to_request_response(request, recipient)


async def _respond(
    request_id: uuid.UUID, user: User, friend_repo: FriendRepository, accept: bool
) -> FriendRequestResponse:
    use_case = RespondToFriendRequestUseCase(friend_repo)
    try:
        request = await use_case.execute(request_id, user.id, accept)
    except FriendRequestNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotFriendRequestRecipientError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except FriendRequestAlreadyAnsweredError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return _to_request_response(request, user)


@router.post("/requests/{request_id}/accept", response_model=FriendRequestResponse)
async def accept_friend_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    friend_repo: FriendRepository = Depends(get_friend_repository),
) -> FriendRequestResponse:
    """Accept. Creates the friendship in the same transaction."""
    return await _respond(request_id, current_user, friend_repo, accept=True)


@router.post("/requests/{request_id}/decline", response_model=FriendRequestResponse)
async def decline_friend_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    friend_repo: FriendRepository = Depends(get_friend_repository),
) -> FriendRequestResponse:
    """Decline. The sender may ask again later — the unique index on a pending
    pair is partial, so a declined request does not block a new one."""
    return await _respond(request_id, current_user, friend_repo, accept=False)


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def remove_friend(
    friend_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    friend_repo: FriendRepository = Depends(get_friend_repository),
) -> None:
    """Unfriend. Symmetric — it ends for both sides."""
    try:
        await RemoveFriendUseCase(friend_repo).execute(current_user.id, friend_id)
    except NotFriendsError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
