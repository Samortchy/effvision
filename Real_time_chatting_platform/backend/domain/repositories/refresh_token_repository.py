from __future__ import annotations
from abc import ABC, abstractmethod
import uuid

from domain.entities.refresh_token import RefreshToken


class RefreshTokenRepository(ABC):
    """Port for refresh token persistence — creation, lookup, and revocation."""

    @abstractmethod
    async def create(self, user_id: uuid.UUID, token_hash: str, expires_at) -> RefreshToken:
        ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        ...

    @abstractmethod
    async def revoke(self, token_id: uuid.UUID) -> None:
        ...