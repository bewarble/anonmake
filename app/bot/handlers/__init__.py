from app.bot.handlers.admin_stage25_1 import router as admin_stage25_1_router
from app.bot.handlers.admin_stage25 import router as admin_stage25_router
from app.bot.handlers.admin_reply import router as admin_reply_router
from app.bot.handlers.source_management import router as source_management_router
from app.bot.handlers.admin_keyboard import router as admin_keyboard_router
from app.bot.handlers.admin_minimal import router as admin_minimal_router
from app.bot.handlers.admin_bi import router as admin_bi_router
from app.bot.handlers.admin_crm import router as admin_crm_router
from app.bot.handlers.start_marketing import router as start_marketing_router
from app.bot.handlers.admin_marketing import router as admin_marketing_router
from app.bot.handlers.admin_control import router as admin_control_router
from app.bot.handlers.admin_users import router as admin_users_router
from app.bot.handlers.errors import router as errors_router
from app.bot.handlers.admin_analytics import router as admin_analytics_router
from app.bot.handlers.admin_delivery import router as admin_delivery_router
from aiogram import Router

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.admin_system import router as admin_system_router
from app.bot.handlers.answers import router as answers_router
from app.bot.handlers.questions import router as questions_router
from app.bot.handlers.reveals import router as reveals_router
from app.bot.handlers.start import router as start_router


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(admin_stage25_1_router)
    router.include_router(source_management_router)
    router.include_router(errors_router)

    router.include_router(admin_marketing_router)
    router.include_router(admin_crm_router)
    router.include_router(admin_users_router)
    router.include_router(admin_analytics_router)
    router.include_router(admin_delivery_router)
    router.include_router(admin_system_router)
    router.include_router(start_marketing_router)
    router.include_router(start_router)
    router.include_router(questions_router)
    router.include_router(reveals_router)
    router.include_router(answers_router)

    return router


__all__ = ("build_router",)
