from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import get_current_user
from api.dependencies.repositories import get_refresh_token_repository, get_user_repository
from application.dto.auth_dto import LoginRequest, RefreshTokenRequest, LogoutRequest, StreamTicketResponse, TokenResponse, RegisterRequest, RegisterResponse
from core import stream_tickets
from domain.entities.user import User
from application.use_cases.auth.login import LoginUseCase
from application.use_cases.auth.refresh_token import RefreshTokenUseCase
from application.use_cases.auth.logout import LogoutUseCase
from application.use_cases.users.register_user import RegisterUserUseCase, DuplicateUserError
from domain.exceptions import InvalidCredentialsError, InvalidTokenError, UserNotFoundError
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from domain.repositories.user_repository import UserRepository

#router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix = "/auth", tags = ["Authentication"])

@router.post("/register", response_model = RegisterResponse, status_code = 201)
async def  register(data: RegisterRequest, repo: UserRepository = Depends(get_user_repository)):
    use_case = RegisterUserUseCase(repo)
    try:
        return await use_case.execute(data.username, data.email, data.password)
    except DuplicateUserError as e:
        raise HTTPException(status_code = 409, detail = f"Duplicate user entry in {e.field} --- user already registered")


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> TokenResponse:
    use_case = LoginUseCase(user_repo, refresh_token_repo)
    try:
        access_token, refresh_token = await use_case.execute(payload.identifier, payload.password)
    except InvalidCredentialsError as e:
        # str(e) is the deliberately vague message from the use case — it must
        # stay identical for "unknown user" and "wrong password".
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


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


@router.post("/stream-ticket", response_model=StreamTicketResponse)
async def issue_stream_ticket(current_user: User = Depends(get_current_user)) -> StreamTicketResponse:
    """Exchange a bearer token for a one-shot ticket to open an SSE stream.

    Authenticated by header, like everything else — the ticket exists purely so
    that the credential which ends up in the stream URL (and therefore in logs
    and browser history) is not the access token itself.
    """
    return StreamTicketResponse(
        ticket=stream_tickets.issue(current_user.id),
        expires_in=stream_tickets.TICKET_TTL_SECONDS,
    )


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