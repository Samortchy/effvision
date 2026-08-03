from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

from domain.entities.user import User


class UserRepository(ABC):
    """Port (interface) for user persistence. Concrete implementation lives in
    infrastructure/repositories/user_repository_sqla.py. Use cases depend on
    this interface only — never on the concrete SQLAlchemy class directly."""

    @abstractmethod
    async def create_user(self, username: str, email: str, password_hash: str) -> User:
        """Persist a new user and return it with the DB-generated id/created_at.

        Takes the already-hashed password, never the plaintext — hashing is the
        use case's job, and the repository must not be a place a raw password can
        reach. Uniqueness of username/email is enforced by the DB, so a caller
        that pre-checks still has to handle IntegrityError.
        """
        ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        ...

    @abstractmethod
    async def search_by_username(self, query: str, limit: int, offset: int) -> list[User]:
        ...

    @abstractmethod
    async def update_last_seen(self, user_id: uuid.UUID, timestamp: datetime) -> None:
        ...

    @abstractmethod
    async def update(self, user: User) -> None:
        ...