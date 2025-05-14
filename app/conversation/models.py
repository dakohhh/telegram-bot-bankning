from uuid import UUID
from enum import Enum
from typing import Optional, TYPE_CHECKING
from ..database.models import BaseModel
from sqlmodel import Field, Relationship, Enum as ColumnEnum, Column

if TYPE_CHECKING:
    from ..user.models import User

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Conversation(BaseModel, table=True):
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    user: Optional["User"] = Relationship(back_populates="conversation")
    messages: list["Message"] = Relationship(back_populates="conversation", cascade_delete=True)

    @property
    def get_messages(self) -> dict:
        _messages = []

        for message in self.messages:
            _messages.append(
                {
                    "role": message.role,
                    "content": message.content
                }
            )

        return _messages


class Message(BaseModel, table=True):
    content: str
    role: MessageRole = Field(sa_column=Column(ColumnEnum(MessageRole)))
    conversation_id: Optional[UUID] = Field(default=None, foreign_key="conversation.id", ondelete="CASCADE")
    conversation: Optional["Conversation"] = Relationship(back_populates="messages")