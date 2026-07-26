from aiogram.fsm.state import State, StatesGroup


class SourceCreate(StatesGroup):
    waiting_name = State()
    waiting_url = State()
    waiting_spend = State()


class BroadcastCreate(StatesGroup):
    waiting_kind = State()
    waiting_audience = State()
    waiting_text = State()
    waiting_confirm = State()
