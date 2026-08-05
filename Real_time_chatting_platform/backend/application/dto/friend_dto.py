from __future__ import annotations
from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict

from application.dto.user_dto import UserSummary


class SendFriendRequestRequest(BaseModel):
    user_id: uuid.UUID


class FriendRequestResponse(BaseModel):
    """A pending request, with whoever is on the other end of it.

    `user` is the counterpart, not the caller — the sender on an incoming
    request, the recipient on an outgoing one. Without it the client would have
    a bare id and no endpoint to turn it into a name.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    status: Literal["pending", "accepted", "declined"]
    created_at: datetime
    responded_at: datetime | None = None
    user: UserSummary
