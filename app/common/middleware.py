from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from ..database.config import get_session, ensure_database_connection
from typing import Callable, Dict, Any, Awaitable
from ..user.service import UserService
from ..conversation.service import ConversationService
import asyncio
import logging

logger = logging.getLogger(__name__)

class CustomAiogramMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.connection_errors = 0
        self.max_connection_errors = 3

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        max_retries = 3
        for attempt in range(max_retries):
            session = None
            try:
                # Get session with timeout
                session_generator = get_session()
                session = await asyncio.wait_for(
                    session_generator.__anext__(), 
                    timeout=10.0
                )
                
                data["session"] = session
                
                # Set up services with the current session
                data["user_service"] = UserService(session)
                data["conversation_service"] = ConversationService(session)
                
                # Process the handler
                result = await handler(event, data)
                
                # Ensure session is committed if needed
                await session.commit()
                
                # Reset connection error counter on success
                self.connection_errors = 0
                
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                is_connection_error = any(keyword in error_msg for keyword in [
                    'connection', 'interface', 'timeout', 'pool', 'asyncpg'
                ])
                
                if session:
                    try:
                        await session.rollback()
                    except:  # noqa: E722
                        pass  # Ignore rollback errors on broken connections
                    
                    try:
                        await session.close()
                    except:  # noqa: E722
                        pass  # Ignore close errors on broken connections
                
                if is_connection_error:
                    self.connection_errors += 1
                    logger.error(f"Database connection error (attempt {attempt + 1}): {e}")
                    
                    if attempt < max_retries - 1:
                        # Wait before retrying
                        await asyncio.sleep(1 * (attempt + 1))
                        
                        # Try to recover connection if we've had multiple errors
                        if self.connection_errors >= self.max_connection_errors:
                            logger.info("Multiple connection errors detected, attempting recovery...")
                            try:
                                await ensure_database_connection()
                                self.connection_errors = 0
                            except Exception as recovery_error:
                                logger.error(f"Connection recovery failed: {recovery_error}")
                        
                        continue
                
                # Re-raise non-connection errors or if all retries failed
                logger.error(f"Middleware error: {e}")
                raise e
            
            finally:
                # Ensure session is always closed
                if session:
                    try:
                        await session.close()
                    except:  # noqa: E722
                        pass
        
        # If we get here, all retries failed
        raise Exception("All database connection attempts failed")