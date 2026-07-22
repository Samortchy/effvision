from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.security import decode_token

# Step 1: knows how to pull the raw token string out of the
# "Authorization: Bearer <token>" header on incoming requests.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    STUB — Day 1 version. Verifies the JWT and returns the user_id string
    from its payload. Does NOT hit the database yet, so it can't confirm
    the user still exists.

    Ismail, Day 2 Task 2: replace the return value with a real User object
    fetched via UserRepository.
    """
    # Step 2: validate the token, get back its payload (or None if invalid,
    # expired, or a refresh token being passed off as an access token).
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id