from __future__ import annotations

from core.security import decode_token, hash_token
from domain.exceptions import InvalidTokenError
from domain.repositories.refresh_token_repository import RefreshTokenRepository


class LogoutUseCase:
    def __init__(self, refresh_token_repo: RefreshTokenRepository):
        self.refresh_token_repo = refresh_token_repo

    async def execute(self, raw_refresh_token: str) -> None:
        payload = decode_token(raw_refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid refresh token")

        token_hash = hash_token(raw_refresh_token)
        stored_token = await self.refresh_token_repo.get_by_token_hash(token_hash)
        if stored_token is None:
            raise InvalidTokenError("Refresh token not found")

        await self.refresh_token_repo.revoke(stored_token.id)