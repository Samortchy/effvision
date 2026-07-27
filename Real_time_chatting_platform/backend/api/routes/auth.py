from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.repositories import get_refresh_token_repository, get_user_repository
from application.dto.auth_dto import RefreshTokenRequest, LogoutRequest, TokenResponse
from application.use_cases.auth.refresh_token import RefreshTokenUseCase
from application.use_cases.auth.logout import LogoutUseCase
from domain.exceptions import InvalidTokenError, UserNotFoundError
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from domain.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshTokenRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> TokenResponse:
    use_case = RefreshTokenUseCase(user_repo, refresh_token_repo)
    try:
        access_token, refresh_token = await use_case.execute(payload.refresh_token)
    except (InvalidTokenError, UserNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> None:
    use_case = LogoutUseCase(refresh_token_repo)
    try:
        await use_case.execute(payload.refresh_token)
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))