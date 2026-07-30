from domain.repositories.user_repository import UserRepository 
from application.dto.user_dto import UserProfileResponse

class UserNotFound(Exception):
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found")

class GetUserProfileUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> UserProfileResponse:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFound(user_id)
        return UserProfileResponse(
            id = user.id,
            username = user.username,
            email = user.email,
            display_name = user.display_name,
            avatar_url = user.avatar_url,
            bio = user.bio,
            status = user.status,
            last_seen_at = getattr(user, 'last_seen_at', None),
            created_at = user.created_at
        )
