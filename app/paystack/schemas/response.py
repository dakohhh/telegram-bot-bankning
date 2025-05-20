from pydantic import BaseModel, Field

from .transfer_recipient import TransferRecipient
from .customer import Customer
from .dva import DVA
from .bank import Bank
from .resolve_account import ResolveAccount

class PaystackResponse(BaseModel):
    status: bool
    message: str

class PaystackSuccessResponse(PaystackResponse):
    """Paystack Success Response"""

class PaystackErrorResponse(PaystackResponse):
    """Paystack Error Response"""

class PaystackCreatedCustomerSuccessResponse(PaystackSuccessResponse):
    data: Customer

class PaystackCreatedDedicatedAccountResponse(PaystackSuccessResponse):
    data: DVA


class PaystackGetBanksResponse(PaystackSuccessResponse):
    data: list[Bank]

class PaystackResolveBankResponse(PaystackSuccessResponse):
    data: ResolveAccount

class PaystackCreateTransferRecipient(PaystackSuccessResponse):
    data: TransferRecipient
