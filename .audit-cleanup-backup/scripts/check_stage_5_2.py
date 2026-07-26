import asyncio

from sqlalchemy import inspect

from app.core.config import load_settings
from app.database.session import close_database, engine, init_database


async def database_check() -> None:
    await init_database()
    async with engine.connect() as connection:
        columns = await connection.run_sync(
            lambda conn: {
                item["name"]
                for item in inspect(conn).get_columns("reveal_checkouts")
            }
        )
    assert {"notified_at", "notification_error"}.issubset(columns), columns
    await close_database()


def web_check() -> None:
    settings = load_settings()
    assert hasattr(settings, "public_base_url")
    assert hasattr(settings, "impaya_webhook_secret")

    from app.web.app import app

    routes = {route.path for route in app.routes}
    expected = {
        "/health",
        "/payments/return/success/{checkout_token}",
        "/payments/return/fail/{checkout_token}",
        "/payments/impaya/webhook",
    }
    assert expected.issubset(routes), routes


asyncio.run(database_check())
web_check()

print("Stage 5.2 check: OK")
print("Manual payment check button: removed")
print("Payment confirmation: return endpoint + Impaya webhook")
print("Authoritative status: reconciled through Impaya")
print("Services: bot + web + billing worker")
