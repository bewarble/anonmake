from __future__ import annotations

from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin_reply import (
    broadcast_kind_keyboard,
    referral_sources_keyboard,
)
from app.core.config import load_settings
from app.repositories.marketing import MarketingRepository
from app.services.admin_bi import AdminBIService
from app.services.admin_charts import growth_chart, profit_chart

router = Router(name="admin_reply")


def is_admin(telegram_id: int) -> bool:
    return telegram_id in load_settings().admin_ids_set


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",")


@router.message(F.text == "Статистика")
async def statistics(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await AdminBIService(session).statistics()
    image = BufferedInputFile(
        growth_chart(data.points),
        filename="statistics.png",
    )

    caption = (
        "📊 Статистика\n\n"
        f"• Всего — {number(data.users_total)}\n"
        f"• Активны — {number(data.users_active_30d)}\n"
        f"• Недоступны — {number(data.users_unreachable)}\n\n"
        "👤 Статистика по времени\n\n"
        f"• За сегодня — {number(data.today)}\n"
        f"• За неделю — {number(data.week)}\n"
        f"• За месяц — {number(data.month)}\n\n"
        "📈 Органический прирост\n\n"
        f"• За сегодня — {number(data.organic_today)}\n"
        f"• За неделю — {number(data.organic_week)}\n"
        f"• За месяц — {number(data.organic_month)}\n\n"
        f"Активных ссылок — {number(data.active_sources)}"
    )

    await message.answer_photo(image, caption=caption)


@router.message(F.text == "Прибыль")
async def profit(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await AdminBIService(session).profit()
    image = BufferedInputFile(
        profit_chart(data.points),
        filename="profit.png",
    )

    caption = (
        "👤 Статистика по прибыли\n\n"
        f"• За сегодня — {money(data.revenue_today)} ₽ "
        f"({money(data.profit_today)} ₽) "
        f"+{number(data.payments_today)} оплат\n"
        f"• За неделю — {money(data.revenue_week)} ₽ "
        f"({money(data.profit_week)} ₽) "
        f"+{number(data.payments_week)} оплат\n"
        f"• За месяц — {money(data.revenue_month)} ₽ "
        f"({money(data.profit_month)} ₽) "
        f"+{number(data.payments_month)} оплат"
    )

    await message.answer_photo(image, caption=caption)


@router.message(F.text == "Выгрузка")
async def export(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    payload = await AdminBIService(session).export_users_csv()
    await message.answer_document(
        BufferedInputFile(
            payload,
            filename="anonmake-users.csv",
        ),
        caption="📄 Выгрузка готова",
    )


@router.message(F.text == "Рассылка")
async def broadcast(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    await message.answer(
        "📢 Рассылка\n\nВыберите тип сообщения.",
        reply_markup=broadcast_kind_keyboard(),
    )


@router.message(F.text == "Рефералы")
async def referrals(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    sources = await MarketingRepository(session).sources()
    if not sources:
        text = (
            "📣 Рефералы\n\n"
            "Ссылок пока нет.\n"
            "Создайте первую рекламную ссылку."
        )
    else:
        text = (
            "📣 Рефералы\n\n"
            f"Активных ссылок: {len(sources)}\n"
            "Выберите ссылку для просмотра статистики."
        )

    await message.answer(
        text,
        reply_markup=referral_sources_keyboard(sources),
    )
