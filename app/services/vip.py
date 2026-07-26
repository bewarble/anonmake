from datetime import datetime, timezone

from app.models.billing import Subscription


def has_active_vip(subscription: Subscription | None) -> bool:
    """Access remains active until access_until even when auto-renew is disabled."""
    if subscription is None or subscription.access_until is None:
        return False

    access_until = subscription.access_until
    if access_until.tzinfo is None:
        access_until = access_until.replace(tzinfo=timezone.utc)

    return access_until > datetime.now(timezone.utc)
