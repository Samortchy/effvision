from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import uuid


class Broadcaster(ABC):
    """Port for real-time event delivery. Concrete implementation wraps the
    actual WebSocket connection manager (infrastructure/websocket).

    The method name matches the only consumer (TypingIndicatorUseCase) and the
    adapter; it is deliberately not just `broadcast`, because a future fan-out
    to a single user rather than a room would need a sibling method.
    """

    @abstractmethod
    async def broadcast_to_conversation(
        self,
        conversation_id: uuid.UUID,
        event: dict[str, Any],
        exclude_user_id: uuid.UUID | None = None,
    ) -> None:
        """Deliver `event` to every live subscriber of the conversation.

        `exclude_user_id` skips one participant — used to avoid echoing an
        event back to the client that caused it.
        """
        ...
