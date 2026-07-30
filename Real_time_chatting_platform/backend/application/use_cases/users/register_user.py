from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from application.dto.auth_dto import RegisterResponse

from core.security import hash_password
import structlog

logger = structlog.get_logger()

class DuplicateUserError(Exception):
    def __init__(self, field: str):
        self.field = field
        super().__init__(f"Duplicate user entry in {self.field}")

class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, username: str, email: str, password: str) -> RegisterResponse:
        existing_user_by_username = await self.user_repository.get_by_username(username)
        if existing_user_by_username:
            raise DuplicateUserError(username)

        existing_user_by_email = await self.user_repository.get_by_email(email)
        if existing_user_by_email:
            raise DuplicateUserError(email)

        password_hash = hash_password(password)

        new_user = User(
            id = None,
            password_hash = password_hash,
            email = email,
            username = username
        )

        created = await self.user_repository.create(new_user)

        logger.info("Registering new user", username = username, email = email)
        return RegisterResponse(id = created.id, username = created.username, email = created.email)
           




