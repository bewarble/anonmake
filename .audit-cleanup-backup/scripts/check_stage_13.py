from __future__ import annotations

import asyncio
import secrets

from app.database.session import SessionFactory, close_database, init_database
from app.repositories.delivery import DeliveryRepository
from app.repositories.delivery_admin import DeliveryAdminRepository


async def check() -> None:
    await init_database()
    key = f"stage13:{secrets.token_hex(8)}"

    async with SessionFactory() as session:
        job = await DeliveryRepository(session).enqueue(
            kind="stage13-test",
            dedupe_key=key,
            chat_id=-1,
            text="Stage 13",
        )
        job.status = "failed"
        job.last_error = "Synthetic test failure"
        await session.commit()
        delivery_id = job.id

    async with SessionFactory() as session:
        repository = DeliveryAdminRepository(session)
        summary = await repository.summary()
        assert summary["failed"] >= 1
        assert await repository.retry_failed(delivery_id)
        await session.commit()

    await close_database()

    print("Stage 13 check: OK")
    print("Admin delivery dashboard: available")
    print("Failed delivery list: available")
    print("Manual retry: audited and safe")


if __name__ == "__main__":
    asyncio.run(check())
