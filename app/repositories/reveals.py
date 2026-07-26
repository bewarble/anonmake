from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reveal import RevealCheckout


class RevealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self,
        *,
        question_id: int,
        buyer_id: int,
    ) -> RevealCheckout:
        result = await self.session.execute(
            select(RevealCheckout).where(
                RevealCheckout.question_id == question_id,
                RevealCheckout.buyer_id == buyer_id,
            )
        )
        checkout = result.scalar_one_or_none()
        if checkout is not None:
            return checkout

        checkout = RevealCheckout(
            question_id=question_id,
            buyer_id=buyer_id,
        )
        self.session.add(checkout)
        await self.session.flush()
        return checkout

    async def get_by_token(
        self,
        token: str,
        *,
        for_update: bool = False,
    ) -> RevealCheckout | None:
        statement = select(RevealCheckout).where(RevealCheckout.token == token)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_customer_operation_id(
        self,
        customer_operation_id: str,
        *,
        for_update: bool = False,
    ) -> RevealCheckout | None:
        statement = select(RevealCheckout).where(
            RevealCheckout.customer_operation_id == customer_operation_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
