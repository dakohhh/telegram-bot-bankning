from pydantic import BaseModel

class ResolveAccount(BaseModel):
    account_number: str
    account_name: str
    bank_id: int

# "account_number": "0001234567",
#     "account_name": "Doe Jane Loren",
#     "bank_id": 9