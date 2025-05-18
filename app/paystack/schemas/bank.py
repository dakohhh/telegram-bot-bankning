from pydantic import BaseModel

class Bank(BaseModel):
    name: str
    id: int
    slug: str
    code: str
    currency: str
    type: str
    active: bool