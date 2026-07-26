from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import select

from app.database.session import SessionFactory, close_database, init_database
from app.models import Answer, Question, User
from app.repositories import AnswerRepository, QuestionRepository


async def check() -> None:
    await init_database()

    suffix = secrets.randbelow(10**12)
    sender_tg_id = -(suffix * 2 + 1)
    recipient_tg_id = -(suffix * 2 + 2)

    async with SessionFactory() as session:
        sender = User(
            telegram_id=sender_tg_id,
            username="stage3_sender",
            first_name="Sender",
        )
        recipient = User(
            telegram_id=recipient_tg_id,
            username="stage3_recipient",
            first_name="Recipient",
        )
        session.add_all([sender, recipient])
        await session.flush()

        question = await QuestionRepository(session).create(
            sender_id=sender.id,
            recipient_id=recipient.id,
            text="Stage 3 test question",
        )
        await AnswerRepository(session).create(
            question=question,
            text="Stage 3 test answer",
        )

        loaded = await QuestionRepository(session).get_with_users(question.id)
        assert loaded is not None
        assert loaded.sender.telegram_id == sender_tg_id
        assert loaded.recipient.telegram_id == recipient_tg_id
        assert loaded.answer is not None
        assert loaded.answer.text == "Stage 3 test answer"
        assert loaded.status == "answered"

        table_names = {
            User.__tablename__,
            Question.__tablename__,
            Answer.__tablename__,
        }
        assert table_names == {"users", "questions", "answers"}

        # Keep the local database clean after verification.
        await session.rollback()

    async with SessionFactory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id.in_([sender_tg_id, recipient_tg_id]))
        )
        assert result.scalars().all() == []

    await close_database()

    print("Stage 3 check: OK")
    print("Tables: users, questions, answers")
    print("Flow: question -> answer")


if __name__ == "__main__":
    asyncio.run(check())
