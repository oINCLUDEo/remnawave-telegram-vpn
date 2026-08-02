"""Mobile /me endpoint — returns current user profile and subscription info."""

from __future__ import annotations

from datetime import UTC

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_current_cabinet_user
from app.config import settings
from app.database.models import User
from app.mobile.schemas.me import MeMobileResponse


logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get(
    '/me',
    response_model=MeMobileResponse,
    summary='Профиль текущего пользователя',
    description='Возвращает данные авторизованного пользователя и его подписку. Требует Bearer-токен.',
    tags=['mobile'],
)
async def get_me(
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> MeMobileResponse:
    """Return profile and subscription data for the authenticated mobile user."""
    try:
        if user.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Учётная запись заблокирована',
            )

        await db.refresh(user, ['subscriptions'])
        subscription = getattr(user, 'subscription', None)
        # Load tariff relationship while the session is still open so we can
        # include the plan name in the response without lazy-load errors.
        if subscription is not None and getattr(subscription, 'tariff_id', None):
            await db.refresh(subscription, ['tariff'])

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile /me DB error', user_id=user.id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обращении к базе данных',
        ) from exc

    # ── Build subscription dict ───────────────────────────────────────────
    sub_data: dict | None = None
    if subscription is not None:
        end_date = getattr(subscription, 'end_date', None)
        expire_ts: int | None = None
        if end_date is not None:
            try:
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=UTC)
                expire_ts = int(end_date.timestamp())
            except (AttributeError, ValueError, OSError):
                expire_ts = None

        traffic_limit_gb = getattr(subscription, 'traffic_limit_gb', 0) or 0
        traffic_used_gb = getattr(subscription, 'traffic_used_gb', 0.0) or 0.0
        purchased_traffic_gb = getattr(subscription, 'purchased_traffic_gb', 0) or 0
        total_gb = traffic_limit_gb + purchased_traffic_gb

        tariff = getattr(subscription, 'tariff', None)
        plan_name: str | None = getattr(tariff, 'name', None) or None

        # Reserve-squad grace: status/end_date are kept ACTIVE internally so the
        # periodic status checker doesn't flap the record back to expired every
        # cycle (see grant_reserve_squad_grace) — but the app must not show this
        # as a normal active subscription. Surface the real picture instead, and
        # report the actual small grace traffic cap rather than the underlying
        # tariff's limit (which is not what's enforced on the panel right now).
        is_reserve_grace = getattr(subscription, 'reserve_access_granted_at', None) is not None

        sub_data = {
            'status': getattr(subscription, 'status', 'unknown'),
            'is_trial': bool(getattr(subscription, 'is_trial', False)),
            'is_reserve_grace': is_reserve_grace,
            'expire_at': expire_ts,
            'traffic_limit_gb': settings.RESERVE_GRACE_TRAFFIC_GB if is_reserve_grace else total_gb,
            'traffic_used_gb': round(traffic_used_gb, 3),
            'subscription_url': getattr(subscription, 'subscription_url', None),
            'device_limit': getattr(subscription, 'device_limit', 1),
            'autopay_enabled': bool(getattr(subscription, 'autopay_enabled', False)),
            'plan_name': plan_name,
        }

    balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)
    balance_currency_raw = getattr(user, 'balance_currency', None)
    balance_currency = balance_currency_raw.upper() if isinstance(balance_currency_raw, str) else 'RUB'

    return MeMobileResponse(
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        has_subscription=subscription is not None,
        subscription=sub_data,
        balance_kopeks=balance_kopeks,
        balance_rub=round(balance_kopeks / 100, 2),
        balance_currency=balance_currency,
    )
