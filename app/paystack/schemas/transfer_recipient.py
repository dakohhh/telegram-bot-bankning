from pydantic import BaseModel

class TransferRecipient(BaseModel):
    active: bool
    id: int
    name: str
    recipient_code: str