from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bot_context import require_current_bot
from app.models.admin import AdminAuditLog
from app.models.billing import PaymentMethod, Subscription
from app.repositories.billing import BillingRepository
from app.services.billing import BillingService, ChargeResult
from app.services.impaya import ImpayaClient


@dataclass(slots=True)
class AdminActionResult:
    ok: bool
    message: str
    attempt_id: int | None = None


class AdminSubscriptionControl:
    """Internal support actions with locking, validation and an audit trail."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        admin_username: str,
        client: ImpayaClient | None = None,
        primary_amount: int = 29900,
        fallback_amount: int = 9900,
        primary_days: int = 3,
        fallback_days: int = 1,
    ) -> None:
        self.session = session
        self.repo = BillingRepository(session)
        self.admin_username = admin_username
        self.client = client
        self.primary_amount = primary_amount
        self.fallback_amount = fallback_amount
        self.primary_days = primary_days
        self.fallback_days = fallback_days

    @staticmethod
    def _require_current_subscription(subscription: Subscription) -> None:
        if subscription.bot_id != require_current_bot().id:
            raise ValueError("Subscription does not belong to the current bot")

    async def charge(
        self,
        subscription: Subscription,
        method: PaymentMethod | None,
        *,
        plan: str,
    ) -> AdminActionResult:
        self._require_current_subscription(subscription)
        if self.client is None:
            return AdminActionResult(False, "Платёжный клиент недоступен.")

        if method is None:
            return AdminActionResult(False, "У пользователя нет привязанной карты.")
        if method.bot_id != subscription.bot_id or method.user_id != subscription.user_id:
            raise ValueError("Payment method does not belong to the subscription project/user")
        if not method.is_active or not method.is_recurrent:
            return AdminActionResult(False, "Платёжная привязка неактивна.")
        if not method.binding_id or not method.impaya_user_id:
            return AdminActionResult(False, "Платёжная привязка заполнена не полностью.")

        locked = await self.repo.try_subscription_lock(subscription.id)
        if not locked:
            return AdminActionResult(
                False,
                "Подписка уже обрабатывается другим процессом. Повторите позже.",
            )

        try:
            await self.session.refresh(subscription)

            if plan == "primary":
                amount = self.primary_amount
                period = timedelta(days=self.primary_days)
                kind = "admin_primary"
            elif plan == "fallback":
                amount = self.fallback_amount
                period = timedelta(days=self.fallback_days)
                kind = "admin_fallback"
            else:
                return AdminActionResult(False, "Неизвестный тариф.")

            result: ChargeResult = await BillingService(
                self.session,
                self.client,
                primary_amount=self.primary_amount,
                primary_duration=timedelta(days=self.primary_days),
                fallback_amount=self.fallback_amount,
                fallback_duration=timedelta(days=self.fallback_days),
            ).test_charge(
                subscription,
                method,
                amount=amount,
                access_period=period,
                kind=kind,
            )

            await self._audit(
                action="subscription.manual_charge",
                target=f"subscription:{subscription.id}",
                details={
                    "bot_id": subscription.bot_id,
                    "plan": plan,
                    "amount_kopecks": amount,
                    "decision": result.decision.value,
                    "attempt_id": result.attempt.id,
                    "error_code": result.attempt.error_code,
                },
            )
            await self.session.commit()

            if result.successful:
                return AdminActionResult(
                    True,
                    f"Списание {amount / 100:.2f} ₽ выполнено успешно.",
                    result.attempt.id,
                )

            return AdminActionResult(
                False,
                (
                    f"Списание отклонено: "
                    f"{result.attempt.error_code or result.decision.value}."
                ),
                result.attempt.id,
            )
        finally:
            await self.repo.release_subscription_lock(subscription.id)
            await self.session.commit()

    async def set_auto_renew(
        self,
        subscription: Subscription,
        *,
        enabled: bool,
    ) -> AdminActionResult:
        self._require_current_subscription(subscription)
        now = datetime.now(timezone.utc)

        if enabled:
            await self.repo.lock_subscription_transaction(subscription.id)
            await self.session.refresh(subscription)
            subscription.auto_renew = True
            subscription.cancelled_at = None
            subscription.next_charge_at = (
                subscription.access_until
                if subscription.access_until and subscription.access_until > now
                else now
            )
            subscription.status = (
                "active_1_day"
                if subscription.access_until and subscription.access_until > now
                else "past_due"
            )
        else:
            await self.repo.cancel_auto_renew(subscription, cancelled_at=now)

        await self._audit(
            action="subscription.auto_renew",
            target=f"subscription:{subscription.id}",
            details={"bot_id": subscription.bot_id, "enabled": enabled},
        )
        await self.session.commit()
        return AdminActionResult(
            True,
            "Автопродление включено." if enabled else "Автопродление отключено.",
        )

    async def extend_access(
        self,
        subscription: Subscription,
        *,
        days: int,
    ) -> AdminActionResult:
        self._require_current_subscription(subscription)
        if days not in {1, 3}:
            return AdminActionResult(False, "Недопустимый срок продления.")

        await self.repo.lock_subscription_transaction(subscription.id)
        await self.session.refresh(subscription)
        now = datetime.now(timezone.utc)
        base = max(subscription.access_until or now, now)
        subscription.access_until = base + timedelta(days=days)
        if subscription.auto_renew:
            subscription.next_charge_at = subscription.access_until
        subscription.status = f"active_{days}_day" if days == 1 else "active_3_days"
        subscription.cancelled_at = None if subscription.auto_renew else subscription.cancelled_at

        await self._audit(
            action="subscription.manual_extend",
            target=f"subscription:{subscription.id}",
            details={
                "bot_id": subscription.bot_id,
                "days": days,
                "access_until": subscription.access_until.isoformat(),
            },
        )
        await self.session.commit()
        return AdminActionResult(True, f"VIP статус продлён на {days} дн.")

    async def _audit(
        self,
        *,
        action: str,
        target: str,
        details: dict,
    ) -> None:
        # The historical column is named admin_telegram_id, but web admin
        # authenticates by username. Store a deterministic neutral value and
        # preserve the username inside details until the audit schema evolves.
        self.session.add(
            AdminAuditLog(
                admin_telegram_id=0,
                action=action,
                target=target,
                details=json.dumps(
                    {"admin_username": self.admin_username, **details},
                    ensure_ascii=False,
                ),
            )
        )
