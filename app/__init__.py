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

from .paystack.client import PaystackClient
from .paystack.error import PaystackException

from .common.utils.helpers import load_file_to_memory, ogg_to_wav_bytes

from .clover.models.inputs import TransferMoneyInput
from .clover.parsers import PhotoTransferMoneyParser, BankCodeParser

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

    final_text = ""

    if message.text:
        final_text = message.text

    elif message.photo:
        photo = await load_file_to_memory(bot, message.photo[-1])

        parser = PhotoTransferMoneyParser()

        transfer_money_input = await parser.parse(photo)

        if transfer_money_input.account_number:
            final_text = final_text + f"Account number: {transfer_money_input.account_number}, "

        if transfer_money_input.bank_name:
            final_text = final_text + f"Bank Name: {transfer_money_input.bank_name}"

    if message.voice:
        voice = await load_file_to_memory(bot, message.voice)

        voice_wav_io = ogg_to_wav_bytes(voice)

        from openai import OpenAI
        client = OpenAI()

        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe", 
            file=voice_wav_io,
        )

        final_text = transcription.text


    await conversation_service.add_messages_to_conversation(content=f"UserID: {str(user.id)}", role=MessageRole.USER, conversation_id=conversation.id)
    await conversation_service.add_messages_to_conversation(content=final_text, role=MessageRole.USER, conversation_id=conversation.id)

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
    async def verify_bank_name(bank_name: str) -> str:
        """Checks if the bank is a valid bank returns a bank code to initiate the transfer"""
        paystack_client = PaystackClient()

        banks = (await paystack_client.get_banks()).data

        bank_data = ""

        for bank in banks:
           bank_data = bank_data + f"Bank Name: {bank.name} => Bank Code: {bank.code}\n"

        bank_code_parser = BankCodeParser()

        bank_code = bank_code_parser.parse(bank_name, bank_data).bank_code
        
        return bank_code
        

    @function_tool
    async def verify_recipient(account_number: str, bank_code: str) -> str:
        """Verifies and returns the recipient's name based on account number and bank code. The bank_code is a """
        print(f"[Tool Call]: Verifying recipient with account {account_number} at {bank_code}")
        print(f"[Tool Call]: Verifying recipient with account {account_number} at {bank_code}")
        print(f"[Tool Call]: Verifying recipient with account {account_number} at {bank_code}")
        
        try:
            paystack_client = PaystackClient()

            resolve_account = (await paystack_client.resolve_account(account_number=account_number, bank_code=bank_code)).data

        except PaystackException as error:
            print(error)
            return "Sorry! Could not resolve the account name, please check the account number and bank name again"
        

        await conversation_service.add_messages_to_conversation(
                content=f"New Bank Code To Transfer: {bank_code}", 
                role=MessageRole.ASSISTANT, 
                conversation_id=conversation.id
            )
            
        return f"Account Name: {resolve_account.account_name}, Account Number: {resolve_account.account_number}, Bank Code: {bank_code}"
    
    @function_tool
    async def send_money(account_number: str, amount: int, bank_code: str) -> bool:
        """Transfers money to a bank account."""
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank_code}")
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank_code}")
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank_code}")
        return True


    agent = Agent(
        name="Clover AI Assistant",
        instructions=(
            "You're Clover, the AI assistant for Cleva Banking. "
            "Use the provided tools whenever possible and do not rely on your own knowledge. "
            "If the queries provided require no tools, simply give a reply that says you do not have that feature yet. "
            
            "For money transfers/send money, follow this exact process: "
            
            "1. Make sure the user has supplied the Account Number, Bank Name, and the Amount they want to transfer. "
            "Ask for any missing information before proceeding. "
            
            "2. Verify if balance is sufficient using check_user_balance_is_sufficient. "
            "If the balance is insufficient, inform the user and stop the process. "
            
            "3. IMPORTANT: Convert the bank name to a bank code using the verify_bank_name tool. "
            "Store this bank code value in your conversation memory. "
            "Never display the bank code to the user or mention its existence. "
            
            "4. Use the verify_recipient tool with the account_number and the bank_code obtained in step 3 (NOT the bank name). "
            "Show the account holder's name to the user and ask for confirmation. "
            
            "5. CRITICAL: Use the EXACT SAME bank_code from step 3 when calling the send_money tool. "
            "Do NOT recalculate or look up the bank code again. "
            "For example, if you determined the bank code is '070' in step 3, use '070' in this step as well. "
            "Call the send_money tool with the account number, amount, and the SAME bank_code used for verification. "
            
            "The primary currency is Nigerian Naira (₦). "
            
            "STATE MANAGEMENT: You must maintain state throughout the conversation. "
            "Once you obtain a bank code for a specific bank, you must use the same bank code "
            "throughout all subsequent steps of that particular transaction. DO NOT recalculate "
            "or look up the bank code multiple times for the same transaction."
        ),
        model="gpt-4o-mini",
        tools=[check_user_balance, check_user_balance_is_sufficient, verify_bank_name, verify_recipient, send_money]
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