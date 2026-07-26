from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.question import Question


class AnswerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, question: Question, text: str) -> Answer:
        answer = Answer(question_id=question.id, text=text)
        question.status = "answered"
        self.session.add(answer)
        await self.session.flush()
        return answer
