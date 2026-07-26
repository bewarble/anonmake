from aiogram.fsm.state import State, StatesGroup


class CrmNoteCreate(StatesGroup):
    waiting_text = State()


class CrmTagCreate(StatesGroup):
    waiting_name = State()
