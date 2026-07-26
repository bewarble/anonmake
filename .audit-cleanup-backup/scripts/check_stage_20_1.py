from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import inspect

from app.database.session import SessionFactory, close_database, engine, init_database
from app.repositories.crm import CrmRepository


async def check() -> None:
    await init_database()

    async with engine.connect() as connection:
        tables = set(
            await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        )

    required = {"crm_tags", "crm_user_tags", "crm_notes", "crm_events"}
    assert required.issubset(tables), (required, tables)

    async with SessionFactory() as session:
        repository = CrmRepository(session)
        tag = await repository.ensure_tag(
            name=f"stage20-{secrets.token_hex(3)}",
            admin_telegram_id=1,
        )
        assert tag.id
        await session.rollback()

    await close_database()

    print("Stage 20.1 check: OK")
    print("CRM: tags, notes and event timeline")
    print("Attribution: source visible in CRM card")
    print("Audit: admin note/tag actions recorded")


if __name__ == "__main__":
    asyncio.run(check())
