from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Question, User
from app.models.admin import AdminAuditLog
from app.models.billing import PaymentAttempt, Subscription


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dashboard(self) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)

        users = await self.session.scalar(select(func.count(User.id)))
        questions = await self.session.scalar(select(func.count(Question.id)))
        answers = await self.session.scalar(select(func.count(Answer.id)))
        vip = await self.session.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.access_until.is_not(None),
                Subscription.access_until > now,
            )
        )
        new_users = await self.session.scalar(
            select(func.count(User.id)).where(User.created_at >= day_ago)
        )
        new_questions = await self.session.scalar(
            select(func.count(Question.id)).where(Question.created_at >= day_ago)
        )

        return {
            "users": int(users or 0),
            "questions": int(questions or 0),
            "answers": int(answers or 0),
            "vip": int(vip or 0),
            "new_users_24h": int(new_users or 0),
            "new_questions_24h": int(new_questions or 0),
        }

    async def payments(self) -> dict[str, int]:
        success_amount = await self.session.scalar(
            select(func.coalesce(func.sum(PaymentAttempt.amount_kopecks), 0)).where(
                PaymentAttempt.status == "success"
            )
        )
        success_count = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(
                PaymentAttempt.status == "success"
            )
        )
        failed_count = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(
                PaymentAttempt.status == "failed"
            )
        )
        pending_count = await self.session.scalar(
            select(func.count(PaymentAttempt.id)).where(
                PaymentAttempt.status == "pending"
            )
        )
        return {
            "success_amount_kopecks": int(success_amount or 0),
            "success_count": int(success_count or 0),
            "failed_count": int(failed_count or 0),
            "pending_count": int(pending_count or 0),
        }

    async def find_user(self, query: str) -> User | None:
        normalized = query.strip()
        if normalized.startswith("@"):
            normalized = normalized[1:]

        conditions = [func.lower(User.username) == normalized.casefold()]
        if normalized.isdigit():
            conditions.extend(
                [
                    User.telegram_id == int(normalized),
                    User.id == int(normalized),
                ]
            )

        result = await self.session.execute(
            select(User).where(or_(*conditions)).limit(1)
        )
        return result.scalar_one_or_none()

    async def subscription_for_user(self, user_id: int) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def grant_vip(self, user_id: int, days: int) -> Subscription:
        now = datetime.now(timezone.utc)
        subscription = await self.subscription_for_user(user_id)

        if subscription is None:
            subscription = Subscription(
                user_id=user_id,
                status="admin_granted",
                auto_renew=False,
            )
            self.session.add(subscription)
            await self.session.flush()

        current = subscription.access_until
        if current is None:
            base = now
        else:
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            base = max(current, now)

        subscription.access_until = base + timedelta(days=days)
        subscription.status = "admin_granted"
        subscription.auto_renew = False
        subscription.next_charge_at = None
        await self.session.flush()
        return subscription

    async def revoke_vip(self, user_id: int) -> Subscription | None:
        subscription = await self.subscription_for_user(user_id)
        if subscription is None:
            return None

        subscription.access_until = datetime.now(timezone.utc)
        subscription.auto_renew = False
        subscription.next_charge_at = None
        subscription.status = "admin_revoked"
        await self.session.flush()
        return subscription

    async def audit(
        self,
        *,
        admin_telegram_id: int,
        action: str,
        target: str | None = None,
        details: str | None = None,
    ) -> None:
        self.session.add(
            AdminAuditLog(
                admin_telegram_id=admin_telegram_id,
                action=action,
                target=target,
                details=details,
            )
        )

    async def recent_audit(self, limit: int = 10) -> list[AdminAuditLog]:
        result = await self.session.execute(
            select(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())
