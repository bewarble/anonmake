import asyncio
import secrets

from sqlalchemy import select

from app.database.session import SessionFactory, close_database, init_database
from app.models.user import User


async def check() -> None:
    await init_database()

    telegram_id = -secrets.randbelow(10**15) - 1
    public_code = secrets.token_urlsafe(9)

    async with SessionFactory() as session:
        user = User(
            telegram_id=telegram_id,
            public_code=public_code,
            username="stage_2_2_check",
            first_name="Stage",
            last_name="Check",
        )
        session.add(user)
        await session.flush()

        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        stored_user = result.scalar_one()

        assert stored_user.id is not None
        assert stored_user.public_code == public_code
        assert stored_user.first_name == "Stage"
        assert stored_user.created_at is not None
        assert stored_user.updated_at is not None

        # The verification row must not remain in the local database.
        await session.rollback()

    await close_database()

    print("Stage 2.2 check: OK")
    print("User model: users")


if __name__ == "__main__":
    asyncio.run(check())
