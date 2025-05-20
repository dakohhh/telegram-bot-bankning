from typing import Optional
from pydantic import BaseModel

class Bank(BaseModel):
    name: str
    id: Optional[int] = None
    slug: Optional[str] = None
    code: Optional[str] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    active: Optional[bool] = None