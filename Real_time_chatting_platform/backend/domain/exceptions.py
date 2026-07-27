class DomainError(Exception):
    """Base class for all domain-level errors."""


class InvalidTokenError(DomainError):
    """Raised when a refresh token is invalid, expired, or revoked."""


class UserNotFoundError(DomainError):
    """Raised when a referenced user no longer exists."""