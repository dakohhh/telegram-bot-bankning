from pydantic import BaseModel
from .customer import Customer
from .dva import DVA

class PaystackSuccessResponse(BaseModel):
    status: bool
    message: str

class PaystackCreatedCustomerSuccessResponse(PaystackSuccessResponse):
    data: Customer

class PaystackCreatedDedicatedAccountResponse(PaystackSuccessResponse):
    data: DVA