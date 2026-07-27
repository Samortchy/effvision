class DomainError(Exception):
    """Base class for all domain-level errors."""


class InvalidTokenError(DomainError):
    """Raised when a refresh token is invalid, expired, or revoked."""


class UserNotFoundError(DomainError):
    """Raised when a referenced user no longer exists."""


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
