from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.crm import CrmRepository


async def record_crm_event(
    session: AsyncSession,
    *,
    user_id: int,
    event_type: str,
    summary: str,
    external_key: str | None = None,
) -> None:
    await CrmRepository(session).record_event(
        user_id=user_id,
        event_type=event_type,
        summary=summary,
        external_key=external_key,
    )
