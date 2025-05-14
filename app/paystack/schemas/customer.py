from pydantic import BaseModel

class Customer(BaseModel):
    id: int
    email: str
    customer_code: str
    integration: int
    domain: str
    identified: bool