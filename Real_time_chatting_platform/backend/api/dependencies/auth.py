from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from api.dependencies.repositories import get_user_repository
from core.security import decode_token
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from application.use_cases.users.update_last_seen import UpdateLastSeenUseCase

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

from application.dto.auth_dto import RegisterResponse, RegisterRequest
from application.use_cases.users.register_user import RegisterUserUseCase, DuplicateUserError

# Same scheme, but tolerates a missing header so the caller can fall back to
# another carrier (see get_current_user_sse).
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _authenticate(token: str | None, user_repo: UserRepository) -> User:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    update_last_seen = UpdateLastSeenUseCase(user_repo)
    await update_last_seen.execute(user.id, user.last_seen_at)

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    return await _authenticate(token, user_repo)


async def get_current_user_sse(
    header_token: str | None = Depends(optional_oauth2_scheme),
    token: str | None = Query(
        default=None,
        description=(
            "Access token. Only for SSE/EventSource clients, which cannot set an "
            "Authorization header; prefer the header everywhere else."
        ),
    ),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Auth for SSE endpoints.

    The browser EventSource API accepts no custom headers, so the token may also
    arrive as a query parameter. That puts it in access logs and in the Referer of
    anything the page loads next, so it stays scoped to the SSE routes and the
    header keeps priority when both are present.
    """
    return await _authenticate(header_token or token, user_repo)
