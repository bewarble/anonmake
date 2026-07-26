import asyncio

from sqlalchemy import inspect

from app.database.session import close_database, engine, init_database


async def check() -> None:
    await init_database()
    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )
    assert "admin_audit_logs" in tables, tables
    await close_database()

    from app.bot.keyboards.admin import admin_menu, user_actions

    assert len(admin_menu().inline_keyboard) == 3
    assert len(user_actions(1).inline_keyboard) == 3

    print("Stage 9 check: OK")
    print("Admin access: ADMIN_IDS")
    print("Dashboard: users, messages, answers, VIP")
    print("Operations: user search, grant/revoke VIP, audit log")
    print("Broadcasts and destructive database actions: not included")


if __name__ == "__main__":
    asyncio.run(check())
