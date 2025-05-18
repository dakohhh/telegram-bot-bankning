import httpx
from typing import Optional
from app.settings import settings
from functools import lru_cache
from app.common.exception import TelegramBankingException
from .error import PaystackException
from .schemas.response import PaystackCreatedCustomerSuccessResponse, PaystackCreatedDedicatedAccountResponse, PaystackErrorResponse,  PaystackGetBanksResponse, PaystackResolveBankResponse

class PaystackClient:
    def __init__(self):
        self.base_url: str = settings.PAYSTACK_BASE_URL
        self.secret_key = settings.PAYSTACK_SECRET_KEY

        self.headers = httpx.Headers()

        # Add a header
        self.headers["Authorization"] = f"Bearer {self.secret_key}"
        self.headers["Content-Type"] = "application/json"

        self.timeout = 30  # Timeout in 30 seconds

    async def get(self, path=None, params=None):
        url = f"{self.base_url}{path}" if path is not None else f"{self.base_url}"

        async with httpx.AsyncClient() as session:
            try:
                response = await session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout

                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError:
                message = dict(response.json()).get("message")
                raise PaystackException(message=message)

            except Exception as error:
                print(error)
                # Use Sentry to log unexpected errors
                raise error

    async def post(self, path=None, data=None, json=None):
        url = f"{self.base_url}{path}" if path is not None else f"{self.base_url}"

        async with httpx.AsyncClient() as session:
            try:
                response = await session.post(
                    url,
                    headers=self.headers,
                    data=data,
                    json=json,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError:
                message = dict(response.json()).get("message")
                raise PaystackException(message=message)

            except Exception as error:
                print(error)
                # Use Sentry to log unexpected errors
                raise

    @lru_cache
    async def get_banks(self, currency: str = "NGN") -> PaystackGetBanksResponse:

        data = await self.get(
            path="/bank/", 
            params={
                "currency": currency
            }
        )

        return PaystackGetBanksResponse(**data)

    # @lru_cache
    async def resolve_account(self, account_number: str, bank_code: str):

        data = await self.get(
            path="/bank/resolve", 
            params={
                "account_number": account_number, 
                "bank_code": bank_code
            } 
        )

        return PaystackResolveBankResponse(**data)

    async def create_transfer_recipient(self, *, name: str, account_number: str, bank_code: str, type: str = "nuban", currency: str = "NGN"):

        data = await self.post(
            path="/transferrecipient/", 
            data={
                "name": name,
                "type": type,
                "currency": currency,
                "bank_code": bank_code,
                "account_number": account_number,
            }
        )

        return data

    async def initiate_transfer(self, * , source: str = "balance", amount: float, reference: str, reason: str):

        response = await self.post(
            path="/transfer/", 
            data={
                "source": source,
                "amount": amount,
                "reference": reference,
                "reason": reason
            }
        )

        return response
    
    async def create_dedicated_account(self, customer_code: str, preferred_bank: str = "wema-bank", phone: str = None):
        """
        Create a dedicated NUBAN account for a Paystack customer.
        """
        payload = {
            "customer": customer_code,
            "preferred_bank": preferred_bank,
        }

        if phone:
            payload["phone"] = phone

        response = await self.post(
            path="/dedicated_account",
            json=payload
        )

        return PaystackCreatedDedicatedAccountResponse(**response)
    

    async def create_customer(
            self,
            *,
            email: str,
            first_name: Optional[str] = None, 
            last_name: Optional[str] = None,
            phone: Optional[str] = None
        ):
        """
        Create a Customer for a Paystack customer.
        """
        payload = { "email": email }

        if first_name:
            payload["first_name"] = first_name

        if last_name:
            payload["last_name"] = last_name

        if phone:
            payload["phone"] = phone

        response = await self.post(
            path="/customer",
            json=payload
        )

        return PaystackCreatedCustomerSuccessResponse(**response)


def handle_paystack(response: httpx.Response):
    if response.json().get("code") == "insufficient_balance":
        raise TelegramBankingException(message="You cannot withdraw now, please try again later")