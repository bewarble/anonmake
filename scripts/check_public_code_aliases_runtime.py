from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.database.session import SessionFactory


async def main_async() -> None:
    async with SessionFactory() as session:
        alias_table = await session.scalar(
            text("SELECT to_regclass('user_public_code_aliases') IS NOT NULL")
        )
        assert alias_table, "user_public_code_aliases table is missing"

        bridge_table = await session.scalar(
            text("SELECT to_regclass('public_code_rotation_snapshot') IS NOT NULL")
        )
        assert not bridge_table, "public_code_rotation_snapshot was not cleaned up by 0027"

        orphan = (
            await session.execute(
                text(
                    """
                    SELECT a.id, a.bot_id, a.user_id, a.public_code
                      FROM user_public_code_aliases a
                 LEFT JOIN users u
                        ON u.id = a.user_id
                       AND u.bot_id = a.bot_id
                     WHERE u.id IS NULL
                     LIMIT 1
                    """
                )
            )
        ).mappings().first()
        assert orphan is None, f"orphan/cross-project public-code alias: {dict(orphan)}"

        conflict = (
            await session.execute(
                text(
                    """
                    SELECT
                        a.id AS alias_id,
                        a.bot_id,
                        a.user_id AS alias_user_id,
                        u.id AS current_user_id,
                        a.public_code
                      FROM user_public_code_aliases a
                      JOIN users u
                        ON u.bot_id = a.bot_id
                       AND u.public_code = a.public_code
                       AND u.id <> a.user_id
                     LIMIT 1
                    """
                )
            )
        ).mappings().first()
        assert conflict is None, f"public-code alias conflicts with current user: {dict(conflict)}"

        duplicate = (
            await session.execute(
                text(
                    """
                    SELECT bot_id, public_code, COUNT(*) AS total
                      FROM user_public_code_aliases
                  GROUP BY bot_id, public_code
                    HAVING COUNT(*) > 1
                     LIMIT 1
                    """
                )
            )
        ).mappings().first()
        assert duplicate is None, f"duplicate public-code alias: {dict(duplicate)}"

        alias_count = int(
            await session.scalar(text("SELECT COUNT(*) FROM user_public_code_aliases"))
            or 0
        )

    print("Public code alias runtime check: OK")
    print(f"Historical aliases checked: {alias_count}")
    print("Alias ownership and active-code conflicts: clean")
    print("Bridge snapshot table: cleaned up")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
