from decimal import Decimal
from uuid import UUID
from .models import User
from ..dva.models import DVA
from sqlmodel import select
from ..settings import settings
from ..database.config import CustomAsyncSession
from ..paystack.client import PaystackClient

class UserService:
    def __init__(self, session: CustomAsyncSession):
        self.session = session

    async def register(
            self, 
            *, 
            telegram_id: int,
            chat_id: str,
            first_name: str, 
            last_name: str,
            email: str,
            phone_number: str
        ) -> User:
        """
        Register a new user with the given user_id, name, and email.
        """

        user = User(
            first_name=first_name,
            last_name=last_name,
            telegram_id=telegram_id,
            phone_number=phone_number,
            email=email,
            chat_id=chat_id
        )

        new_user = await self.session.save(user)

        paystack_client = PaystackClient()

        # Create a paystack customer 
        paystack_customer = await paystack_client.create_customer(email=new_user.email, first_name=new_user.first_name, last_name=user.last_name, phone=new_user.phone_number)

        new_user.customer_code = paystack_customer.data.customer_code

        await self.session.save(new_user)

        # Setup DVA
        paystack_dva = await paystack_client.create_dedicated_account(
            customer_code=new_user.customer_code,
            preferred_bank="wema-bank" if settings.ENVIRONMENT == "production" else "test-bank"
        )

        create_dva = DVA(
            account_name= paystack_dva.data.account_name,
            account_number=paystack_dva.data.account_number,
            bank_name=paystack_dva.data.bank.name,
            currency=paystack_dva.data.currency,
            user_id=new_user.id,
        )

        # Create the DVA account
        await self.session.save(create_dva)

        # Get the user
        new_user = await self.session.find_by_id(obj=User, id=new_user.id, populated_fields=[User.dva])

        # Create Account DVA here
        return new_user

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:

        query = await self.session.exec(select(User).where(User.telegram_id == telegram_id))

        user = query.first()

        return user
    

    async def get_user_dva(self, user_id: UUID) -> DVA | None:

        query = await self.session.exec(select(DVA).where(DVA.user_id == user_id))

        dva = query.first()

        return dva

    
    def check_if_user_registered(self, user_id: int,) -> None:
        """
        Register a new user with the given user_id, name, and email.
        """
       
        print(f"Registering user: {user_id}")

    
    async def get_user_balance(self, user_id: UUID) -> Decimal:
        """
        Gets the user's balance.
        """

        query = await self.session.exec(select(User.balance).where(User.id == user_id))

        balance = query.first()

        return balance