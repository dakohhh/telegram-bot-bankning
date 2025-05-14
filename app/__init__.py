import os
import asyncio
from typing import Optional
from uuid import UUID
from sqlmodel import SQLModel  # noqa: F401
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.types import Message

from app.conversation.models import Conversation, MessageRole
from app.conversation.service import ConversationService

# Initialize database models and import them in correct order
# First import base models
from .database.models import BaseModel, UUIDModel, TimestampModel  # noqa: F401
# Then import specific models in their dependency order
from .user.models import User  # noqa: F401
from .dva.models import DVA  # noqa: F401

from .user.service import UserService
from .user.states import CreateUserForm
from .database.config import CustomAsyncSession
from .common.middleware import CustomAiogramMiddleware

# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)

dp = Dispatcher()

dp.message.middleware(CustomAiogramMiddleware())

@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext, user_service: UserService, conversation_service: ConversationService) -> None:
    user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)
    if user:
        await message.answer(
            f"Welcome back {user.first_name} {user.last_name} 👋\n\n"
            "1. 💰 Check balance — type `/balance`\n"
            "2. 📥 Deposit funds — type `/deposit`\n"
            "3. 💸 Send money — type `/send`\n"
        )
        conversation = await conversation_service.create_conversation(user_id=user.id)

        await state.update_data(current_conversation=conversation)

    else:
        await message.answer(
            "Welcome to Cleva Banking 👋\n"
            "I'm Cleva, your AI-powered banking assistant.\n\n"
            "Looks like you haven't opened an account with us:\n"
            "To open your cleva account — type `/register`\n"
        )

@dp.message(Command("register"))
async def command_register_handler(message: Message, session: CustomAsyncSession) -> None:
    user_service = UserService(session=session)
    existing_user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)

    if existing_user:
        await message.answer(
            "You already have an account with us 👋\n"
        )
        await command_dashboard_handler()
    else:

        # Start the FSM to collect email and phone number 
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Share Contact", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            "Please share your phone number by clicking the button below:",
            reply_markup=keyboard
        )


@dp.message(F.contact)
async def phone_contact_handler(message: Message, state: FSMContext) -> None:
    print(f"Phone number received: {message.contact.phone_number}")

    await state.update_data(phone_number=message.contact.phone_number)

    await message.answer("Next, type a valid email address 😁")

    # Proceed to the next state to collect the email
    await state.set_state(CreateUserForm.waiting_for_email)


@dp.message(CreateUserForm.waiting_for_email)
async def email_handler(message: Message, state: FSMContext) -> None:
    email = message.text 

    print(f"Email received: {email}")

    await state.update_data(email=email)
    
    data = await state.get_data()

    await message.answer(
        "Please confirm your details \n"
        f"Email: {data["email"]} \n"
        f"Phone Number: {data["phone_number"]} \n"
        "if this information are correct, type 'yes' else 'no'"
    )

    # Proceed to the next state to confirm and register the user
    await state.set_state(CreateUserForm.waiting_confirm_create_user_form)


@dp.message(CreateUserForm.waiting_confirm_create_user_form)
async def proceed_registration(message: Message, state: FSMContext, user_service: UserService) -> None:
    confirm_text = message.text.lower()

    if confirm_text == "no":
       await message.answer("Registration is cancelled ❌, type /register to start over")
       return
    
    elif confirm_text == "yes":
        data = await state.get_data()

        new_user: User = await user_service.register(
            telegram_id=message.from_user.id, 
            first_name=message.from_user.first_name, 
            last_name=message.from_user.last_name,
            phone_number=data["phone_number"],
            email=data["email"]
        )

        print(new_user.model_dump())

        await message.answer(
            "Account Created Successfully ❤️\n"
            f"Welcome {new_user.first_name} {new_user.last_name}! 🤗\n"
            f"Your balance 💵 is:  {new_user.balance}\n\n"

            f"Your account information:"
            f"Account Name:  {new_user.dva.account_name}\n"
            f"Account Number:  {new_user.dva.account_number}\n"
            f"Bank Name:  {new_user.dva.bank_name}\n"
        )

        await message.answer(
            "1. 💰 Check balance — type `/balance`\n"
            "2. 📥 Deposit funds — type `/deposit`\n"
            "3. 💸 Send money — type `/send`\n"
        )



@dp.message(Command("balance"))
async def command_balance_handler(message: Message, session: CustomAsyncSession) -> None:
    user_service = UserService(session=session)
    user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)
    if not user:
         await message.answer(
            "Looks like you haven't opened an account with us 😣\n"
            "To open your cleva account — type `/register`"
        ) 
    else:
        await message.answer(f"Your balance 💵 is:  {user.balance}\n")


@dp.message(Command("dashboard"))
async def command_dashboard_handler(message: Message) -> None:
    print(message.from_user.id)
    await message.answer(
        "Here's what I can do for you:\n"
        "1. 📝 Register account — type `/register`\n"
        "2. 💰 Check balance — type `/balance`\n"
        "3. 📥 Deposit funds — type `/deposit`\n"
        "4. 💸 Send money — type `/send`\n",
    )


@dp.message(Command("deposit"))
async def command_deposit_handler(message: Message) -> None:
    print(message.from_user.id)
    await message.answer(
        "Here's what I can do for you:\n"
        "1. 📝 Register account — type `/register`\n"
        "2. 💰 Check balance — type `/balance`\n"
        "3. 📥 Deposit funds — type `/deposit`\n"
        "4. 💸 Send money — type `/send`\n",
    )

@dp.message()
async def handle_any_message(message: Message, state: FSMContext, user_service:  UserService, conversation_service: ConversationService):
    data = await state.get_data()

    user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)

    conversation: Optional[Conversation] = data.get("current_conversation")

    if not conversation:
        conversation = await conversation_service.create_conversation(user_id=user.id)
        
        await state.update_data(current_conversation=conversation)

    await conversation_service.add_messages_to_conversation(content=f"UserID: {str(user.id)}", role=MessageRole.USER, conversation_id=conversation.id)
    await conversation_service.add_messages_to_conversation(content=message.text, role=MessageRole.USER, conversation_id=conversation.id)

    conversation = await conversation_service.get_conversation_with_messages(conversation_id=conversation.id)

    from agents import Agent, Runner, function_tool

    @function_tool
    async def check_user_balance(user_id: str) -> str:
        """Checks the user's account balance and returns it."""
        
        print(f"[Tool Call]: Checking account balance for user: {user_id}")
        print(f"[Tool Call]: Checking account balance for user: {user_id}")
        print(f"[Tool Call]: Checking account balance for user: {user_id}")
        print(f"[Tool Call]: Checking account balance for user: {user_id}")

        # Assuming `user_service.get_user_balance` is an async function, you need to await it
        balance = await user_service.get_user_balance(UUID(user_id))

        # Return the balance
        return f"You account balance is: {balance}"
    
    @function_tool
    async def check_user_balance_is_sufficient(user_id: str, amount: float) -> str:
        """Checks if the user's account balance is sufficient for the transaction."""
        print(f"[Tool Call]: Checking if account balance is sufficient for user: {user_id}")
        print(f"[Tool Call]: Checking if account balance is sufficient for user: {user_id}")
        print(f"[Tool Call]: Checking if account balance is sufficient for user: {user_id}")
        balance = await user_service.get_user_balance(UUID(user_id))
        if balance >= amount:
            return "Balance is sufficient to make the transfer."
        else:
            return f"Insufficient balance. Your current balance is {balance}₦."
        

    @function_tool
    async def verify_recipient(account_number: str, bank: str) -> str:
        """Verifies and returns the recipient's name based on account number and bank."""
        print(f"[Tool Call]: Verifying recipient with account {account_number} at {bank}")
        print(f"[Tool Call]: Verifying recipient with account {account_number} at {bank}")
        print(f"[Tool Call]: Verifying recipient with account {account_number} at {bank}")
        
        # In a real implementation, this would call your banking API
        # For this example, we'll simulate by returning a mock name
        recipient_names = {
            "0123456789": "John Doe",
            "1234567890": "Mary Smith",
            "2345678901": "David Johnson",
            # Add more mock account numbers and names as needed
        }

        if bank.lower() not in ["maldive", "djoyi"]:
            return "Bank is not on our records, please confirm bank again"
        
        
        # Default for unknown accounts
        default_name = "Unknown Recipient"
        
        # Return the recipient name or default
        return recipient_names.get(account_number, default_name)
    
    @function_tool
    async def send_money(account_number: str, amount: int, bank: str) -> bool:
        """Transfers money to a bank account."""
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank}")
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank}")
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank}")
        return True


    agent = Agent(
        name="Clover AI Assistant",
        instructions=(
            "You're a Clover, the AI assistant for Cleva Banking."
            "Use the provided tools  whenever possible."
            "Do not rely on your own knowledge."
            "Instead use your tools"
            "If the queries provided require no tools, simply give a reply that says you do not have that feature yet."
            "Now if the user query is money transfers/send money follow this exact process: "
            "1. Verify if balance is sufficient using check_user_balance_is_sufficient "
            "2. Then get the bank code using the bank name"
            "3. Verify recipient using verify_recipient tool and ask user to confirm the name "
            "4. Only after user confirmation, call send_money "
            "The primary currency is Nigerian Naira (₦)"
        ),
        model="gpt-4o-mini",
        tools=[check_user_balance, check_user_balance_is_sufficient, send_money, verify_recipient]
    )

    result = await Runner.run(agent, input=conversation.get_messages)

    # Append the result of the agents final output to the  conversation
    if isinstance(result.final_output, str):
        await conversation_service.add_messages_to_conversation(content=result.final_output, role=MessageRole.ASSISTANT, conversation_id=conversation.id)

    await message.answer(result.final_output)


# Run the bot
async def run_bot() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(run_bot())