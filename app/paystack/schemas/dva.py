from pydantic import BaseModel
from .bank import Bank

class DVA(BaseModel):
    account_name: str
    account_number: str
    currency: str
    bank: Bank