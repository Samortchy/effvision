class DomainError(Exception):
    """Base class for all domain-level errors."""


class InvalidTokenError(DomainError):
    """Raised when a refresh token is invalid, expired, or revoked."""


class UserNotFoundError(DomainError):
    """Raised when a referenced user no longer exists."""


class UserAlreadyExistsError(DomainError):
    """Raised when a username or email is already taken.

    `field` is the column name ("username" / "email"), never the value. The
    repository raises this instead of leaking a driver-level IntegrityError, so
    the application layer never has to import SQLAlchemy to handle the race.
    """

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"A user with that {field} already exists")


class InvalidCredentialsError(DomainError):
    """Raised when a login identifier/password pair does not authenticate.

    Deliberately does not distinguish "no such user" from "wrong password" —
    that difference is exactly what turns a login form into an account-existence
    oracle, so both paths raise this same error.
    """


class CannotMessageSelfError(DomainError):
    """Raised when a user tries to start a private conversation with themself."""


class ConversationNotFoundError(DomainError):
    """Raised when a referenced conversation does not exist."""


class NotAConversationMemberError(DomainError):
    """Raised when the *acting* user is not an active member of a conversation."""


class MemberNotFoundError(DomainError):
    """Raised when the *target* of a membership action is not an active member."""


class InsufficientPermissionError(DomainError):
    """Raised when a user attempts a membership action their role does not allow."""


class LastOwnerError(DomainError):
    """Raised when an action would leave a conversation with no owner."""


class CannotLeavePrivateConversationError(DomainError):
    """Raised when a user tries to leave a 1:1 private conversation."""


class MessageNotFoundError(DomainError):
    """Raised when a referenced message does not exist."""


class NotMessageOwnerError(DomainError):
    """Raised when a user attempts to modify a message they didn't send."""


class NotificationNotFoundError(DomainError):
    """Raised when a referenced notification does not exist."""


class NotNotificationOwnerError(DomainError):
    """Raised when a user attempts to act on another user's notification."""
