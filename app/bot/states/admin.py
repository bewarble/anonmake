from aiogram.fsm.state import State, StatesGroup


class AdminLookup(StatesGroup):
    waiting_for_user = State()
