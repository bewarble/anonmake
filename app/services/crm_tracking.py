from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.crm import CrmRepository


class CrmTrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CrmRepository(session)

    async def bot_started(self, *, user_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="bot_started",
            summary="Запустил бота",
            external_key=f"user:{user_id}:bot_started",
        )

    async def attributed_to_source(
        self,
        *,
        user_id: int,
        source_id: int,
        source_name: str,
    ) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="source_attributed",
            summary=f"Пришёл из источника «{source_name}»",
            external_key=f"user:{user_id}:source:{source_id}",
        )

    async def question_sent(self, *, user_id: int, question_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="question_sent",
            summary="Отправил анонимное сообщение",
            external_key=f"question:{question_id}:sender",
        )

    async def question_received(self, *, user_id: int, question_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="question_received",
            summary="Получил анонимное сообщение",
            external_key=f"question:{question_id}:recipient",
        )

    async def answer_sent(self, *, user_id: int, answer_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="answer_sent",
            summary="Ответил на сообщение",
            external_key=f"answer:{answer_id}:sender",
        )

    async def answer_received(self, *, user_id: int, answer_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="answer_received",
            summary="Получил ответ",
            external_key=f"answer:{answer_id}:recipient",
        )

    async def vip_activated(self, *, user_id: int, checkout_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="vip_activated",
            summary="Активировал VIP",
            external_key=f"checkout:{checkout_id}:vip",
        )

    async def sender_revealed(self, *, user_id: int, question_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="sender_revealed",
            summary="Раскрыл отправителя сообщения",
            external_key=f"question:{question_id}:revealed:{user_id}",
        )

    async def payment_succeeded(self, *, user_id: int, checkout_id: int) -> None:
        await self.repository.record_event(
            user_id=user_id,
            event_type="payment_succeeded",
            summary="Успешная оплата VIP",
            external_key=f"checkout:{checkout_id}:payment",
        )
