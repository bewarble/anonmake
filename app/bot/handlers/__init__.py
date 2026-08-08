from copy import deepcopy

from aiogram import Router

from app.core.config import load_settings

from app.bot.handlers.admin_marketing import router as admin_marketing_router
from app.bot.handlers.admin_stage25_1 import router as admin_router
from app.bot.handlers.answers import router as answers_router
from app.bot.handlers.chat_members import router as chat_members_router
from app.bot.handlers.errors import router as errors_router
from app.bot.handlers.navigation import fallback_router as navigation_fallback_router
from app.bot.handlers.navigation import router as navigation_router
from app.bot.handlers.questions import router as questions_router
from app.bot.handlers.recurrent_test import router as recurrent_test_router
from app.bot.handlers.payments import router as payments_router
from app.bot.handlers.reveals import router as reveals_router
from app.bot.handlers.source_management import router as source_management_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.start_marketing import router as start_marketing_router
from app.bot.handlers.subscriptions import router as subscriptions_router


def _fresh_router(router: Router) -> Router:
    """Return an unattached router tree for one Dispatcher instance.

    Handler modules expose router singletons, while managed-bots runs several
    Dispatchers inside one Python process. Attaching those singletons directly
    makes the first Dispatcher own them and causes subsequent bots to fail with
    ``Router is already attached``. A deep copy preserves registered handlers,
    filters and nested routers while keeping parent/observer state isolated.
    """
    return deepcopy(router)


def build_router() -> Router:
    router = Router(name="root")

    # Membership updates are independent of message/FSM flows and keep
    # live/dead user state synchronized with Telegram in real time.
    router.include_router(_fresh_router(chat_members_router))

    # Operational admin handlers must precede generic FSM handlers.
    router.include_router(_fresh_router(admin_router))
    router.include_router(_fresh_router(source_management_router))
    router.include_router(_fresh_router(admin_marketing_router))

    router.include_router(_fresh_router(start_marketing_router))
    router.include_router(_fresh_router(start_router))
    # Navigation commands must be able to interrupt an active FSM cleanly.
    router.include_router(_fresh_router(navigation_router))
    router.include_router(_fresh_router(subscriptions_router))

    if load_settings().payment_test_commands_enabled:
        router.include_router(_fresh_router(payments_router))
        router.include_router(_fresh_router(recurrent_test_router))

    router.include_router(_fresh_router(questions_router))
    router.include_router(_fresh_router(reveals_router))
    router.include_router(_fresh_router(answers_router))
    # Unknown updates are handled only after all functional routers had a chance.
    router.include_router(_fresh_router(navigation_fallback_router))
    router.include_router(_fresh_router(errors_router))
    return router


__all__ = ("build_router",)
