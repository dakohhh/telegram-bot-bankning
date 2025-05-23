import asyncio
from uuid import UUID
from sqlmodel import SQLModel, select
from ..settings.config import settings
from typing import Any, Optional, Sequence, Union
from typing import AsyncGenerator, TypeVar
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine

async_database_uri = settings.DATABASE_URL
if async_database_uri.startswith("postgres://"):
    async_database_uri = async_database_uri.replace("postgres://", "postgresql://", 1)

# Convert the PostgreSQL URI to an async URI
# Replace postgresql:// with postgresql+asyncpg://
if not "postgresql+asyncpg://" in async_database_uri:
    async_database_uri = async_database_uri.replace("postgresql://", "postgresql+asyncpg://")

# Enhanced engine configuration for production
engine = create_async_engine(
    async_database_uri,
    # Connection pool settings
    pool_size=20,                    # Number of connections to maintain
    max_overflow=30,                 # Additional connections beyond pool_size
    pool_timeout=30,                 # Timeout when getting connection from pool
    pool_recycle=3600,              # Recycle connections every hour
    pool_pre_ping=True,             # Validate connections before use
    # For debugging connection issues (remove in production)
    echo=False,
    # Connection arguments
    connect_args={
        "server_settings": {
            "application_name": "cleva_banking_bot",
        },
        "command_timeout": 60,
    }
)

# Define a type variable for the model
ModelType = TypeVar('ModelType')

class CustomAsyncSession(AsyncSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def save(self, obj: ModelType, commit: bool = True) -> ModelType:
        self.add(obj)
        if commit:
            await self.commit()
        await self.refresh(obj)
        return obj
    
    async def delete(self, obj: ModelType, commit: bool = True) -> None:
        await super().delete(obj)
        if commit:
            await self.commit()

    async def find_by_id(self, *, obj: ModelType, id: Union[UUID, Any], populated_fields: Optional[Sequence[Any]] = None) -> Optional[ModelType]:
        builder = select(obj).where(obj.id == id)

        if populated_fields:
            for populated_field in populated_fields:
                builder = builder.options(selectinload(populated_field))

        query = await self.exec(builder)
        result = query.first()

        return result

    async def ensure_connection(self):
        """Ensure the connection is still valid"""
        try:
            # Simple query to test connection
            await self.exec(select(1))
        except Exception:
            # Connection is dead, invalidate it
            await self.invalidate()
            raise


async def get_session() -> AsyncGenerator[CustomAsyncSession, None]:
    """Context manager for database sessions with proper cleanup"""
    session = None
    try:
        session = CustomAsyncSession(engine, expire_on_commit=False)
        yield session
    except Exception as e:
        if session:
            await session.rollback()
        raise e
    finally:
        if session:
            await session.close()


async def get_session_for_service() -> CustomAsyncSession:
    """Get a session for service usage - must be manually closed"""
    return CustomAsyncSession(engine, expire_on_commit=False)


# Health check function
async def check_database_health():
    """Check if database connection is healthy"""
    try:
        async with get_session() as session:
            await session.exec(select(1))
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False
    




# Connection recovery function
async def ensure_database_connection():
    """Ensure database connection is available, recreate if necessary"""
    if not await check_database_health():
        print("Database connection unhealthy, attempting to recover...")
        # Force close all connections
        await engine.dispose()
        
        # Wait a moment before reconnecting
        await asyncio.sleep(2)
        
        # Test the connection again
        if await check_database_health():
            print("Database connection recovered successfully")
        else:
            print("Failed to recover database connection")
            raise Exception("Could not establish database connection")
        

# Periodic connection maintenance
async def maintain_database_connections():
    """Periodically check and maintain database connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            if not await check_database_health():
                print("Database connection unhealthy, disposing pool...")
                engine.dispose()
        except Exception as e:
            print(f"Connection maintenance error: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying