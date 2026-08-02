from domain.exceptions import UserAlreadyExistsError
from domain.repositories.user_repository import UserRepository
from application.dto.auth_dto import RegisterResponse

from core.security import hash_password
import structlog

logger = structlog.get_logger()

class DuplicateUserError(Exception):
    """`field` is the column name ("username" / "email"), not the value — the
    value must not reach the client, since it would confirm which address or
    handle is already registered."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"Duplicate user entry in {self.field}")

class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def execute(self, username: str, email: str, password: str) -> RegisterResponse:
        existing_user_by_username = await self.user_repository.get_by_username(username)
        if existing_user_by_username:
            raise DuplicateUserError("username")

        existing_user_by_email = await self.user_repository.get_by_email(email)
        if existing_user_by_email:
            raise DuplicateUserError("email")

        password_hash = hash_password(password)

        try:
            created = await self.user_repository.create_user(username, email, password_hash)
        except UserAlreadyExistsError as exc:
            # The checks above are advisory only: two concurrent registrations
            # can both pass them and race to the INSERT. The unique indexes are
            # what actually decide, so a violation here is the same 409 as above
            # rather than a 500.
            raise DuplicateUserError(exc.field) from exc

        logger.info("Registered new user", user_id = str(created.id), username = username)
        return RegisterResponse(id = created.id, username = created.username, email = created.email)
           




