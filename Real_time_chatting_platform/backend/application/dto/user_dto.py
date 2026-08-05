from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MeResponse(BaseModel):
    """The authenticated user's own profile. Never includes password_hash.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    status: Literal["online", "offline", "away"]
    last_seen_at: datetime | None = None
    created_at: datetime


class UserSummary(BaseModel):
    """search results
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    status: Literal["online", "offline", "away"]


class UpdateProfileRequest(BaseModel):
    """All fields optional (PATCH).
    """
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=2048)
    bio: str | None = Field(default=None, max_length=500)

    def changed_fields(self) -> dict[str, Any]:
        """Only the fields the client actually sent.

        An explicit null is kept (it means "clear this field"); an omitted
        field is absent from the result entirely.
        """
        return self.model_dump(exclude_unset=True)


# class UpdateProfileResponse(BaseModel):
#     """The updated user profile. Never includes password_hash."""
#     model_config =  ConfigDict(extra = "ignore")

#     id: uuid.UUID
#     username: str 
#     display_name: str | None = Field(default=None, max_length=100)
#     avatar_url: str | None = Field(default=None, max_length=2048)
#     email: EmailStr
#     bio: str | None = Field(default=None, max_length=500)
#     status: Literal['online', 'offline', 'away']
#     last_seen_at: datetime | None = None
#     created_at: datetime

class UserProfileResponse(BaseModel):
    """The user profile. Never includes password_hash."""
    model_config =  ConfigDict(extra = "ignore")

    id: uuid.UUID
    username: str 
    display_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=2048)
    email: EmailStr
    bio: str | None = Field(default=None, max_length=500)
    status: Literal['online', 'offline', 'away']
    last_seen_at: datetime | None = None
    created_at: datetime



class UpdateStatusRequest(BaseModel):
    status: Literal["online", "offline", "away"]


class UserSearchQuery(BaseModel):
    """Query params for user search.
    """
    q: str = Field(min_length=1, max_length=50)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
