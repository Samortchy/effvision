from fastapi import APIRouter, Depends

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import get_user_repository
from application.dto.user_dto import UserSearchQuery, UserSummary
from application.use_cases.users.search_users import SearchUsersUseCase
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository

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