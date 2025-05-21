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

engine = create_async_engine(async_database_uri)


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

    async def find_by_id(self,*, obj: ModelType, id: Union[UUID, Any], populated_fields: Optional[Sequence[Any]] = None) -> Optional[ModelType]:

        builder = select(obj).where(obj.id == id)

        if populated_fields:
            for populated_field in populated_fields:
                builder = builder.options(selectinload(populated_field))

        query = await self.exec(builder)

        result = query.first()

        return result


async def get_session() -> AsyncGenerator[CustomAsyncSession, None]:
    async with CustomAsyncSession(engine, expire_on_commit=False) as session:
        yield session
