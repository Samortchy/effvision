from __future__ import annotations
from datetime import datetime, timedelta, timezone

from core.config import settings
from core.security import create_access_token, create_refresh_token, decode_token, hash_token
from domain.exceptions import InvalidTokenError, UserNotFoundError
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from domain.repositories.user_repository import UserRepository


class RefreshTokenUseCase:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo

    async def execute(self, raw_refresh_token: str) -> tuple[str, str]:
        """Returns (new_access_token, new_refresh_token)."""

        payload = decode_token(raw_refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid or expired refresh token")

        token_hash = hash_token(raw_refresh_token)
        stored_token = await self.refresh_token_repo.get_by_token_hash(token_hash)
        if stored_token is None or stored_token.revoked:
            raise InvalidTokenError("Refresh token has been revoked or does not exist")

        user = await self.user_repo.get_by_id(stored_token.user_id)
        if user is None:
            raise UserNotFoundError("User no longer exists")

        # Rotation: revoke the old token before issuing a new pair
        await self.refresh_token_repo.revoke(stored_token.id)

        new_access_token = create_access_token(user.id)
        new_raw_refresh_token = create_refresh_token(user.id)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        await self.refresh_token_repo.create(
            user_id=user.id,
            token_hash=hash_token(new_raw_refresh_token),
            expires_at=new_expires_at,
        )

        return new_access_token, new_raw_refresh_token