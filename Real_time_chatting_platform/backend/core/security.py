from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from core.config import settings

_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        # VerifyMismatchError subclasses VerificationError (wrong password);
        # InvalidHashError covers a NULL/blank/non-argon2 value in the column.
        return False


def _create_token(user_id: str | UUID, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        # str() so callers can pass a UUID primary key directly — a raw UUID
        # is not JSON serializable and would blow up inside jwt.encode.
        "sub": str(user_id),
        "type": token_type,
        "jti": str(uuid4()),  # unique per token, so a single token can be revoked
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str | UUID) -> str:
    return _create_token(
        user_id,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(user_id: str | UUID) -> str:
    return _create_token(
        user_id,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str, expected_type: Literal["access", "refresh"] | None = None) -> dict[str, Any] | None:
    """
    Verify signature + expiry and return the payload, or None if the token is
    unusable. Pass expected_type to also reject a token of the wrong kind —
    without it a long-lived refresh token would pass as an access token.
    """
    try:
        # ExpiredSignatureError subclasses InvalidTokenError, so this covers expiry too.
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError:
        return None

    if expected_type is not None and payload.get("type") != expected_type:
        return None

    return payload