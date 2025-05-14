from uuid import UUID
from typing import Optional, TYPE_CHECKING
from ..database.models import BaseModel
from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from ..user.models import User


class DVA(BaseModel, table=True):
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", unique=True, ondelete="CASCADE")
    user: Optional["User"] = Relationship(back_populates="dva")
    account_name: str
    account_number: str
    bank_name: str
    currency: str