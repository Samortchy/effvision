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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
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