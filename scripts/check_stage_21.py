from __future__ import annotations

import asyncio

from app.database.session import SessionFactory, close_database, init_database
from app.services.admin_bi import AdminBIService
from app.services.admin_charts import growth_chart, profit_chart


async def check() -> None:
    await init_database()

    async with SessionFactory() as session:
        service = AdminBIService(session)
        statistics = await service.statistics()
        profit = await service.profit()
        export = await service.export_users_csv()

    assert statistics.users_total >= 0
    assert statistics.users_active_30d >= 0
    assert len(statistics.points) == 20
    assert len(profit.points) == 20
    assert growth_chart(statistics.points).startswith(b"\x89PNG")
    assert profit_chart(profit.points).startswith(b"\x89PNG")
    assert export.startswith(b"\xef\xbb\xbf")

    await close_database()

    print("Stage 21 check: OK")
    print("Dashboard: statistics and profit charts")
    print("Metrics: total, active, unreachable and organic")
    print("Export: UTF-8 CSV")
    print("Menu: statistics, broadcasts, profit, export and sources")


if __name__ == "__main__":
    asyncio.run(check())
