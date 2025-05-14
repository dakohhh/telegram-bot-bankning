from pydantic import BaseModel

class Bank(BaseModel):
    name: str
    id: int
    slug: str