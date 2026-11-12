from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State()
    phone = State()
    region = State()
    district = State()
    mahalla = State()
    street = State()
    house_number = State()
    lpg_card = State()
    confirm = State()
