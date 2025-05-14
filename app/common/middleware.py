from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from ..database.config import get_session
from typing import Callable, Dict, Any, Awaitable
from ..user.service import  UserService
from ..conversation.service import ConversationService

class CustomAiogramMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async for session in get_session():
            data["session"] = session
            try:
                # Set up services with the current session
                data["user_service"] = UserService(session)
                data["conversation_service"] = ConversationService(session)
                
                # Process the handler
                result = await handler(event, data)
                
                # Ensure session is committed if needed
                await session.commit()
                return result
            except Exception as e:
                # Rollback session on error
                await session.rollback()
                raise e