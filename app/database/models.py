import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import field_serializer
from ..common.utils.pendulum_utc import utc_now


class UUIDModel(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    @field_serializer('id')
    def serialize_id(self, id: uuid.UUID, _info):
        return str(id)


class TimestampModel(SQLModel):
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": utc_now})

    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime , _info):
        return str(created_at)

    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime, _info):
        return str(updated_at)


class BaseModel(UUIDModel, TimestampModel, table=False):
    """Base model for all database models"""