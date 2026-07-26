from aiogram.fsm.state import State, StatesGroup


class AskQuestion(StatesGroup):
    waiting_for_text = State()


class AnswerQuestion(StatesGroup):
    waiting_for_text = State()
