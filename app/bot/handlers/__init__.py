from aiogram import Router

from app.bot.handlers.answers import router as answers_router
from app.bot.handlers.questions import router as questions_router
from app.bot.handlers.reveals import router as reveals_router
from app.bot.handlers.start import router as start_router


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(start_router)
    router.include_router(questions_router)
    router.include_router(reveals_router)
    router.include_router(answers_router)
    return router


__all__ = ("build_router",)
