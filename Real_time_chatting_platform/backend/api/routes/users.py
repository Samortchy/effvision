from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import get_user_repository
from application.dto.user_dto import UserSearchQuery, UserSummary, UserProfileResponse, UpdateProfileRequest
from application.use_cases.users.search_users import SearchUsersUseCase
from application.use_cases.users.update_user_profile import UpdateUserProfileUseCase
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from application.use_cases.users.get_user_profile import GetUserProfileUseCase, UserNotFound


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=list[UserSummary])
async def search_users(
    query: UserSearchQuery = Depends(),
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> list[UserSummary]:
    use_case = SearchUsersUseCase(user_repo)
    users = await use_case.execute(query.q, query.limit, query.offset)
    return [UserSummary.model_validate(u) for u in users]


@router.get("/me", response_model = UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user), repo: UserRepository =  Depends(get_user_repository)):
    
    use_case = GetUserProfileUseCase(repo)
    try:
        return await use_case.execute(current_user.id)

    except UserNotFound:
        # raise, not return: a returned HTTPException is just an object, and
        # FastAPI would try to validate it against response_model and 500.
        raise HTTPException(status_code=404, detail="User not found")


@router.patch("/me", response_model = UserProfileResponse)
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
) -> UserProfileResponse:
    # `payload` is the body; `current_user` is who is making the change. They
    # were previously the same parameter, so the body was never read at all.
    use_case = UpdateUserProfileUseCase(repo)

    try:
        return await use_case.execute(current_user.id, payload)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")



