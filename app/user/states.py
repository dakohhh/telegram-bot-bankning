from aiogram.fsm.state import State, StatesGroup


class CreateUserForm(StatesGroup):
    waiting_for_email = State()
    waiting_confirm_create_user_form = State()