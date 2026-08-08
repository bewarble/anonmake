from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.database.session import SessionFactory


CHECKS = {
    "questions_cross_bot": """
        SELECT count(*)
        FROM questions q
        JOIN users sender ON sender.id = q.sender_id
        JOIN users recipient ON recipient.id = q.recipient_id
        WHERE sender.bot_id <> recipient.bot_id
    """,
    "subscriptions_user_bot_mismatch": """
        SELECT count(*)
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        WHERE s.bot_id <> u.bot_id
    """,
    "payment_methods_user_bot_mismatch": """
        SELECT count(*)
        FROM payment_methods pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.bot_id <> u.bot_id
    """,
    "payment_attempt_subscription_bot_mismatch": """
        SELECT count(*)
        FROM payment_attempts pa
        JOIN subscriptions s ON s.id = pa.subscription_id
        WHERE pa.bot_id <> s.bot_id
    """,
    "source_attribution_bot_mismatch": """
        SELECT count(*)
        FROM source_attributions sa
        JOIN traffic_sources ts ON ts.id = sa.source_id
        JOIN users u ON u.id = sa.user_id
        WHERE ts.bot_id <> u.bot_id
    """,
    "source_click_bot_mismatch": """
        SELECT count(*)
        FROM source_clicks sc
        JOIN traffic_sources ts ON ts.id = sc.source_id
        JOIN users u ON u.id = sc.user_id
        WHERE ts.bot_id <> u.bot_id
    """,
    "reveal_checkout_bot_mismatch": """
        SELECT count(*)
        FROM reveal_checkouts rc
        JOIN users buyer ON buyer.id = rc.buyer_id
        JOIN questions q ON q.id = rc.question_id
        JOIN users sender ON sender.id = q.sender_id
        JOIN users recipient ON recipient.id = q.recipient_id
        WHERE buyer.bot_id <> sender.bot_id
           OR buyer.bot_id <> recipient.bot_id
    """,
    "zero_transaction_ids": """
        SELECT count(*)
        FROM payment_attempts
        WHERE transaction_id = '00000000-0000-0000-0000-000000000000'
    """,
}


async def main_async() -> None:
    async with SessionFactory() as session:
        failures: list[tuple[str, int]] = []
        for name, query in CHECKS.items():
            count = int(await session.scalar(text(query)) or 0)
            print(f"Multibot runtime: {name}={count}")
            if count:
                failures.append((name, count))

        if failures:
            summary = ", ".join(f"{name}={count}" for name, count in failures)
            raise AssertionError(f"Cross-project integrity violations found: {summary}")

    print("Multibot runtime isolation check: OK")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
