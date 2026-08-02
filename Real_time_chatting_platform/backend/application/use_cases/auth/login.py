from __future__ import annotations
from datetime import datetime, timedelta, timezone

import structlog

from core.config import settings
from core.security import create_access_token, create_refresh_token, hash_password, hash_token, verify_password
from domain.exceptions import InvalidCredentialsError
from domain.repositories.refresh_token_repository import RefreshTokenRepository
from domain.repositories.user_repository import UserRepository

logger = structlog.get_logger()

# Verified against once when the identifier matches no user, so that a missing
# account and a wrong password take the same ~argon2 amount of time. Without it
# the response latency alone tells an attacker which usernames are registered.
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


class LoginUseCase:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo

    async def execute(self, identifier: str, password: str) -> tuple[str, str]:
        """Returns (access_token, refresh_token). `identifier` is email or username."""

        # RegisterRequest restricts usernames to [A-Za-z0-9_], so an "@" is an
        # unambiguous signal that the user typed an email.
        if "@" in identifier:
            user = await self.user_repo.get_by_email(identifier)
        else:
            user = await self.user_repo.get_by_username(identifier)

        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Incorrect username/email or password")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Incorrect username/email or password")

        access_token = create_access_token(user.id)
        raw_refresh_token = create_refresh_token(user.id)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        # Only the hash is stored: a leaked refresh_tokens table must not be a
        # set of usable sessions. Same scheme the rotation path in
        # RefreshTokenUseCase writes, so both produce lookup-compatible rows.
        await self.refresh_token_repo.create(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=expires_at,
        )

        logger.info("User logged in", user_id=str(user.id), username=user.username)
        return access_token, raw_refresh_token
