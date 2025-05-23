from decimal import Decimal
import os
import asyncio
from typing import Optional
from uuid import UUID, uuid4
import aio_pika
from sqlmodel import SQLModel, select  # noqa: F401
from dotenv import load_dotenv
from .rabbitmq.client import QueueWrapper, AsyncRabbitMQClient
from email_validator import  validate_email, EmailNotValidError
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession

from app.settings  import settings

from app.conversation.models import Conversation, MessageRole
from app.conversation.service import ConversationService

# Initialize database models and import them in correct order
# First import base models
from .database.models import BaseModel, UUIDModel, TimestampModel  # noqa: F401

from .database.config import get_session
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

from .database.config import maintain_database_connections, check_database_health


# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# Create bot with proper session
bot = Bot(token=TOKEN)

dp = Dispatcher()

dp.message.middleware(CustomAiogramMiddleware())

@dp.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext, user_service: UserService, conversation_service: ConversationService) -> None:
    print(message.chat.id)
    user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)
    if user:
        await message.answer(
            f"Welcome back {user.first_name} {user.last_name} 👋\n\n"
            "1. 💰 Check balance — type `/balance`\n"
            "2. 📥 Deposit funds — type `/deposit`\n"
            "3. For transfers, just interact with the agent 😉."
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


@dp.message(Command("deposit"))
async def command_deposit_handler(message: Message, state: FSMContext, user_service: UserService, conversation_service: ConversationService) -> None:
    user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)
    if user:
        dva = await user_service.get_user_dva(user.id)
        await message.answer(
            "Your Account Information 💲\n\n"
            f"1. Account Number  — {dva.account_number}\n"
            f"1. Account Name  — {dva.account_name}\n"
            f"1. Bank Name — {dva.bank_name}`\n"
            " Send funds to to this account to make a deposit `\n"
        )
    else:
        await message.answer(
            "Oops.. looks like you haven't registered on Cleva Banking 😢\n"
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
        await command_help_handler(message)
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
async def email_handler(message: Message, state: FSMContext, user_service: UserService) -> None:
    # Validate email
    email = None
    try:
        email_info = validate_email(message.text)
        email = email_info.normalized

        existing_user = await user_service.get_user_by_email(email)
        if existing_user:
            await message.answer("Oops..🥲 the email you sent already exists, please provide a valid one")
            return

    except EmailNotValidError:
        await message.answer("Oops..🥲 the email you sent isn't a valid one, please provide a valid one")
        return

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
            email=data["email"],
            chat_id=str(message.chat.id)
        )

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
            "3. For transfers, just interact with the agent 😉."
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


@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    print(message.from_user.id)
    await message.answer(
        "Here's what I can do for you:\n"
        "1. 📝 Register account — type `/register`\n"
        "2. 💰 Check balance — type `/balance`\n"
        "3. 📥 Deposit funds — type `/deposit`\n"
        "3. For transfers, just interact with the agent 😉."

    )


@dp.message()
async def handle_any_message(message: Message, state: FSMContext, user_service: UserService, conversation_service: ConversationService):
    print(message.text)

    data = await state.get_data()

    user = await user_service.get_user_by_telegram_id(telegram_id=message.from_user.id)

    if not user:
        await message.answer(
            "Looks like you haven't opened an account with us 😣\n"
            "To open your cleva account — type `/register`"
        )
        return

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
    async def send_money(user_id: str, account_name: str, account_number: str, amount: int, bank_code: str) -> bool:
        """Transfers money to a bank account."""
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank_code} with account name {account_name}")
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank_code} with account name {account_name}")
        print(f"[Tool Call]: Sending {amount}₦ to account {account_number} at {bank_code} with account name {account_name}")        

        paystack_client = PaystackClient()

        transfer_recipient = (await paystack_client.create_transfer_recipient(name=account_name,account_number=account_number, bank_code=bank_code)).data

        transfer = await paystack_client.initiate_transfer(recipient_code=transfer_recipient.recipient_code, amount=(amount * 100), reference=str(uuid4()))

        # Store the transfer object in the database or something
        print(transfer)

        # Decrement the user's balance
        await user_service.decrement_balance(UUID(user_id), float(amount))

        return True


    agent = Agent(
        name="Clover AI Assistant",
        instructions=(
            "You're Clover, the AI assistant for Cleva Banking. "
            "You are STRICTLY a banking assistant that can ONLY help with cleva banking services. "
            
            "STRICT POLICY: You can ONLY respond to banking related queries. "
            ""
            "For ANY non-banking queries (like entertainment, songs, weather, general knowledge, etc.), "
            "respond with: 'I'm your banking assistant and can only help with banking services. "
            "I can check your balance, help with transfers, or provide account information. "
            "How can I help you with your banking needs today?' "

            "Never display the User ID to the user or mention its existence."

            "Use the provided tools whenever possible and do not rely on your own knowledge. "
            "If the queries provided require no tools, simply give a reply that best suits the query or say you do not have that feature yet. "
            
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

    # Append the result of the agents final output to the conversation
    if isinstance(result.final_output, str):
        await conversation_service.add_messages_to_conversation(
            content=result.final_output, 
            role=MessageRole.ASSISTANT, 
            conversation_id=conversation.id
        )

    

    await message.answer(result.final_output)

async def rabbitmq_listener(session):
    async def on_deposit_call_back(message: aio_pika.abc.AbstractIncomingMessage, session: CustomAsyncSession, bot: Bot):
            import json
            json_data =  json.loads(message.body)

            data = dict(json_data)

            customer_code  = data["customer_code"]
            amount = data["amount"]

            print(customer_code,  amount)

            try:
                # Get the user by the customer code
                query = await session.exec(select(User).where(User.customer_code == customer_code))

                user = query.first()

                user.balance = user.balance + Decimal(str(amount))

                session.add(user)
                await session.commit()
                await session.refresh(user)

                await bot.send_message(
                    user.chat_id, 
                    f"We've received your deposit of ₦{amount} ❤️🤗!\n"
                    f"Your balance is now ₦{user.balance}"
                )
            except Exception as e:
                session.rollback()
                print(e)
                print(e)
                print(e)
                print(e)
                raise e


    rabbitmq_client = AsyncRabbitMQClient(settings.RABBITMQ_URL)
    await rabbitmq_client.connect()
    
    
    # Declare the exchange
    exchange = await rabbitmq_client.declare_exchange("charge")
    
    # Declare the queue
    queue = await rabbitmq_client.declare_queue(queue_name="charge_deposit_queue")
    
    # Bind the queue to the exchange
    await rabbitmq_client.bind_queue(queue, exchange=exchange, routing_key="charge.deposit")
   
    # Subscribe to the queue
    await rabbitmq_client.subscribe([
        QueueWrapper(q=queue, callback=on_deposit_call_back, callback_kwargs={"session": session, "bot": bot})
    ])
    
    return rabbitmq_client




# # Update your run_bot function
# async def run_bot():
#     try:
#         # Check initial database connection
#         if not await check_database_health():
#             raise Exception("Initial database connection failed")
        
#         # Create a task for connection maintenance
#         maintenance_task = asyncio.create_task(maintain_database_connections())
        
#         # Create a task for the message listener
#         async for session in get_session():
#             # Create the proper aiogram session
#             aiogram_session = AiohttpSession(timeout=3600)
#             bot.session = aiogram_session
            
#             rabbitmq_client = await rabbitmq_listener(session)
            
#             # Create polling task
#             polling_task = asyncio.create_task(dp.start_polling(bot))
            
#             # Wait for either task to complete/fail
#             done, pending = await asyncio.wait(
#                 [polling_task, maintenance_task],
#                 return_when=asyncio.FIRST_COMPLETED
#             )
            
#             # Cancel pending tasks
#             for task in pending:
#                 task.cancel()
#                 try:
#                     await task
#                 except asyncio.CancelledError:
#                     pass
            
#             # Check if any task failed
#             for task in done:
#                 if task.exception():
#                     raise task.exception()
            
#             break  # Exit the session loop
            
#     except asyncio.CancelledError:
#         print("Shutting down...")
#     except Exception as e:
#         print(f"Bot error: {e}")
#         # Restart after a delay
#         await asyncio.sleep(5)
#         return await run_bot()  # Recursive restart
#     finally:
#         # Clean up resources
#         if 'rabbitmq_client' in locals():
#             if rabbitmq_client.connection:
#                 await rabbitmq_client.connection.close()
#         # Close the aiogram session
#         if hasattr(bot, 'session'):
#             await bot.session.close()

# # Alternative robust main function with auto-restart
# async def run_bot_with_restart():
#     """Run bot with automatic restart on failure"""
#     while True:
#         try:
#             await run_bot()
#         except Exception as e:
#             print(f"Bot crashed: {e}")
#             print("Restarting in 10 seconds...")
#             await asyncio.sleep(10)

# # Update your __main__ section
# if __name__ == "__main__":
#     # Use the restart-enabled version for production
#     asyncio.run(run_bot_with_restart())





async def run_bot():
    try:
        # Create a task for the message listener
        async for session in get_session():
            # Create the proper aiogram session
            aiogram_session = AiohttpSession(timeout=3600)
            bot.session = aiogram_session
            
            rabbitmq_client = await rabbitmq_listener(session)
            
            # Start the bot
            await dp.start_polling(bot)
            
            # Keep the connection running until the program is terminated
            while True:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Shutting down...")
    finally:
        # Clean up resources
        if 'rabbitmq_client' in locals():
            if rabbitmq_client.connection:
                await rabbitmq_client.connection.close()
        # Close the aiogram session
        if hasattr(bot, 'session'):
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(run_bot())