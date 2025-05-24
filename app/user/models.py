# File: app/user/models.py
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy.sql import expression
from ..database.models import BaseModel
from sqlmodel import Field, Column, Boolean, Numeric, Relationship, BigInteger

if TYPE_CHECKING:
    from ..dva.models import DVA
    from ..conversation.models import Conversation

class User(BaseModel, table=True):
    first_name: Optional[str] = Field(nullable=True)
    last_name: Optional[str] = Field(nullable=True)
    email: str = Field(unique=True)
    phone_number: str
    telegram_id: int = Field(sa_column=Column(BigInteger()))
    chat_id: str
    customer_code: str | None = Field(default=None, nullable=True)
    balance: Decimal = Field(sa_column=Column(Numeric(12, 2), default=Decimal("0.00")))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, nullable=False, server_default=expression.true()))
    
    # String-based relationship reference
    dva: Optional["DVA"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        sa_relationship_kwargs={"uselist": False}
    )

    conversation: Optional["Conversation"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        sa_relationship_kwargs={"uselist": False}
    )