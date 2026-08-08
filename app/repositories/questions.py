from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.bot_context import require_current_bot
from app.models.question import Question
from app.models.user import User


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        sender_id: int,
        recipient_id: int,
        text: str,
        content_type: str = "text",
        media_file_id: str | None = None,
        media_caption: str | None = None,
    ) -> Question:
        bot_id = require_current_bot().id
        sender = await self.session.scalar(
            select(User).where(User.id == sender_id, User.bot_id == bot_id)
        )
        recipient = await self.session.scalar(
            select(User).where(User.id == recipient_id, User.bot_id == bot_id)
        )
        if sender is None or recipient is None:
            raise ValueError("Question participants must belong to the current bot")

        question = Question(
            sender_id=sender_id,
            recipient_id=recipient_id,
            text=text,
            content_type=content_type,
            media_file_id=media_file_id,
            media_caption=media_caption,
        )
        self.session.add(question)
        await self.session.flush()
        return question

    async def get_with_users(
        self,
        question_id: int,
        *,
        for_update: bool = False,
    ) -> Question | None:
        bot_id = require_current_bot().id
        sender = aliased(User)
        recipient = aliased(User)
        statement = (
            select(Question)
            .join(sender, Question.sender_id == sender.id)
            .join(recipient, Question.recipient_id == recipient.id)
            .where(
                Question.id == question_id,
                sender.bot_id == bot_id,
                recipient.bot_id == bot_id,
            )
            .options(
                selectinload(Question.sender),
                selectinload(Question.recipient),
                selectinload(Question.answers),
            )
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
