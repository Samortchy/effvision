from __future__ import annotations

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository


class SearchUsersUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, query: str, limit: int, offset: int) -> list[User]:
        return await self.user_repo.search_by_username(query.strip(), limit, offset)