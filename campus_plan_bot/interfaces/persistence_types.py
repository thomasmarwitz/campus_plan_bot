import uuid
from dataclasses import dataclass
from datetime import datetime

from campus_plan_bot.interfaces.interfaces import (
    ConversationProtocol,
    MessageProtocol,
    Role,
)


@dataclass
class Message(MessageProtocol):
    """Dataclass implementation for a message from the user."""

    id: str
    timestamp: datetime
    content: str
    role: Role

    @classmethod
    def from_content(cls, content: str, role: Role) -> "Message":
        """Convenience method to create a UserMessage with current timestamp
        and random UUID."""
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            content=content,
            role=role,
        )


@dataclass
class Conversation(ConversationProtocol):
    """Dataclass implementation for the conversation history."""

    id: str
    messages: list[MessageProtocol]

    @classmethod
    def new(cls) -> "Conversation":
        """Start a new conversation."""
        id = str(uuid.uuid4())
        return Conversation(
            id=id,
            messages=[],
        )

    def add_message(self, message: MessageProtocol) -> None:
        """Add a message to the conversation history."""
        self.messages.append(message)

    def add_message_from_content(self, content: str, role: Role) -> None:
        """Add a message to the conversation history from content."""
        message = Message.from_content(content, role)
        self.add_message(message)
