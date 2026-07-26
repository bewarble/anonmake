import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.start import router as start_router
from app.core.config import get_settings


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = get_settings()

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
    )

    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(menu_router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
