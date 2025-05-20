import hmac
import hashlib
from app.settings import settings
from contextlib import asynccontextmanager
from .rabbitmq.client import  AsyncRabbitMQClient
from fastapi import FastAPI, HTTPException, Request, status

@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        # rabbitmq_client.connect()
        yield
    finally:
        pass
        # rabbitmq_client.close()


app = FastAPI(lifespan=lifespan)
async def process_charge(data: dict):

    if data["channel"] == "dedicated_nuban":
        customer_code = data["customer"]["customer_code"]
        amount = int(data["amount"]) / 100

        # Publish via rabbitMQ to process deposit

        rabbitmq_client_ = AsyncRabbitMQClient(settings.RABBITMQ_URL)

        exchange  = await rabbitmq_client_.declare_exchange(exchange_name="charge")

        data = { "data": "just some data" }
        
        # Publish message
        await rabbitmq_client_.publish(exchange, "charge.deposit", message={"customer_code": customer_code, "amount": amount})

    print("Processing charge.success event:", data)


async def process_transfer(data: dict):
    print("Processing transfer.success event:", data)


@app.post("/webhook/paystack")
async def handle_paystack_webhook(request: Request):

    raw_body = await request.body()

    if not raw_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

    # Verify signature
    hash_ = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        raw_body,
        hashlib.sha512
    ).hexdigest()

    if hash_ != request.headers["x-paystack-signature"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid paystack signature")

    payload = await request.json()
    payload = dict(payload)

    event = payload.get("event")

    if event == "charge.success":
        data = payload.get("data")
        await process_charge(data)  # Call your charge processing logic here

    return {"message": True}