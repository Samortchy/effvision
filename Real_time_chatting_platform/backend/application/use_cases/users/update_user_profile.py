from domain.repositories.user_repository import UserRepository
from application.dto.user_dto import UpdateProfileRequest, UserProfileResponse
from use_cases.users.get_user_profile import UserNotFound

class UpdateUserProfileUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def execute(self, user_id: str, data: UpdateProfileRequest) -> UserProfileResponse:
        user = await self.user_repository.get_by_id(user_id)

        if not user:
            raise UserNotFound(user_id)
        
        data.model_dump(exclude_unset=True)
        user.avatar_url = data.avatar_url
        user.bio = data.bio
        user.display_name = data.display_name
        user.email = data.email
        user.status = data.status
        user.username = data.username

        updated_user = await self.user_repository.update(user)

        return UserProfileResponse(
            id=updated_user.id, username=updated_user.username, email=updated_user.email,
            display_name=updated_user.display_name, avatar_url=updated_user.avatar_url,
            bio=updated_user.bio, status=updated_user.status,
            last_seen_at=getattr(updated_user, "last_seen_at", None),
        )
