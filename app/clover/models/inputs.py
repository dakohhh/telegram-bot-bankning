from typing import Optional
from pydantic import Field, BaseModel


class TransferMoneyInput(BaseModel):
    """
    Representing transfer details extracted from an uploaded image/document.
    Used to validate and structure the recipient's banking information for money transfers.
    """

    account_number: Optional[str] = Field(description="The recipient's bank account number extracted from the image")
    bank_name: Optional[str] = Field(description="The name of the recipient's bank extracted from the image")