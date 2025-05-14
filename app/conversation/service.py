from uuid import UUID
from .models import Conversation, MessageRole, Message
from sqlmodel import select
from ..settings import settings
from ..database.config import CustomAsyncSession

class ConversationService:
    def __init__(self, session: CustomAsyncSession):
        self.session = session

    async def create_conversation(
            self, 
            *, 
            user_id: UUID,
        ) -> Conversation:
        """
        Creates a new conversation Record.
        """

        create_conversation = Conversation(user_id= user_id)

        new_conversation = await self.session.save(create_conversation)

        return new_conversation
    

    async def get_conversation_with_messages(
            self, 
            *, 
            conversation_id: UUID,
        ) -> Conversation:
        """
        Creates a new conversation Record.
        """

        conversation = await self.session.find_by_id(obj=Conversation, id=conversation_id, populated_fields=[Conversation.messages])

        return conversation
    

    async def add_messages_to_conversation(
        self,
        *,
        content: str,
        role: MessageRole,
        conversation_id: UUID
    ):
        
        create_message = Message(
            content=content,
            role=role,
            conversation_id=conversation_id
        )

        new_message = await self.session.save(create_message)

        return new_message


