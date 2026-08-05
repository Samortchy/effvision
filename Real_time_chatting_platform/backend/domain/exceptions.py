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


class AlreadyAConversationMemberError(DomainError):
    """Raised when adding a user who is already an *active* member.

    Deliberately distinct from "has a membership row": someone who left still
    has one, with `left_at` set, and re-adding them is legitimate.
    """


class CannotAddMembersError(DomainError):
    """Raised when the conversation type does not accept new members.

    A private conversation is exactly two people by definition — growing one
    would silently turn it into a group while every 1:1 lookup still treats it
    as a pair.
    """


class MessageNotFoundError(DomainError):
    """Raised when a referenced message does not exist."""


class NotMessageOwnerError(DomainError):
    """Raised when a user attempts to modify a message they didn't send."""


class CannotFriendSelfError(DomainError):
    """Raised when a user sends themself a friend request."""


class AlreadyFriendsError(DomainError):
    """Raised when a friendship between the two users already exists."""


class FriendRequestAlreadySentError(DomainError):
    """Raised when the sender already has a *pending* request to this user.

    Only pending ones collide — a declined request may be sent again, which is
    exactly why the unique index on the pair is partial.
    """


class IncomingFriendRequestExistsError(DomainError):
    """Raised when the other user has already sent *you* a pending request.

    Not silently auto-accepted: sending a request and accepting one are
    different intentions, and quietly turning the first into the second would
    make a friendship appear from what looked like a one-way action.
    """


class FriendRequestNotFoundError(DomainError):
    """Raised when a referenced friend request does not exist."""


class NotFriendRequestRecipientError(DomainError):
    """Raised when a user tries to answer a request that was not sent to them."""


class FriendRequestAlreadyAnsweredError(DomainError):
    """Raised when accepting or declining a request that is no longer pending."""


class NotFriendsError(DomainError):
    """Raised when removing a friendship that does not exist."""


class NotificationNotFoundError(DomainError):
    """Raised when a referenced notification does not exist."""


class NotNotificationOwnerError(DomainError):
    """Raised when a user attempts to act on another user's notification."""
