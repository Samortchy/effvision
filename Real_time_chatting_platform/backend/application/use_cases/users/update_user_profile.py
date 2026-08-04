from domain.repositories.user_repository import UserRepository
from application.dto.user_dto import UpdateProfileRequest, UserProfileResponse
from application.use_cases.users.get_user_profile import UserNotFound

class UpdateUserProfileUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def execute(self, user_id: str, data: UpdateProfileRequest) -> UserProfileResponse:
        user = await self.user_repository.get_by_id(user_id)

        if not user:
            raise UserNotFound(user_id)

        # PATCH semantics: apply only what the client actually sent. Assigning
        # every field instead would write the request model's `None` defaults
        # over whatever the user already had, so a request carrying just `bio`
        # would silently wipe display_name and avatar_url.
        #
        # The set of writable fields is whatever UpdateProfileRequest declares —
        # display_name, avatar_url, bio. email, username and status are not on
        # that model (and it is extra="forbid"), so a profile PATCH cannot reach
        # them however it is crafted.
        for field, value in data.changed_fields().items():
            setattr(user, field, value)

        updated_user = await self.user_repository.update(user)
        if updated_user is None:
            # The row disappeared between the read and the write.
            raise UserNotFound(user_id)

        return UserProfileResponse(
            id=updated_user.id, username=updated_user.username, email=updated_user.email,
            display_name=updated_user.display_name, avatar_url=updated_user.avatar_url,
            bio=updated_user.bio, status=updated_user.status,
            last_seen_at=updated_user.last_seen_at,
            created_at=updated_user.created_at,
        )
