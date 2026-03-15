"""Mobile /me endpoint — returns current user profile and subscription info."""

from __future__ import annotations

from datetime import UTC

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.crud.user import get_user_by_telegram_id
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
    description=(
        'Возвращает данные авторизованного пользователя и его подписку. '
        'Требует заголовок X-Telegram-Id с Telegram ID пользователя.'
    ),
    tags=['mobile'],
)
async def get_me(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id', description='Telegram user ID'),
) -> MeMobileResponse:
    """Return profile and subscription data for the authenticated mobile user."""
    try:
        db_url = settings.get_database_url()
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

        async with async_session() as db:
            user = await get_user_by_telegram_id(db, x_telegram_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Пользователь не найден',
                )

            if user.status != 'active':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Учётная запись заблокирована',
                )

            await db.refresh(user, ['subscription'])
            subscription = getattr(user, 'subscription', None)

        await engine.dispose()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile /me DB error', telegram_id=x_telegram_id, error=exc)
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

        sub_data = {
            'status': getattr(subscription, 'status', 'unknown'),
            'is_trial': bool(getattr(subscription, 'is_trial', False)),
            'expire_at': expire_ts,
            'traffic_limit_gb': total_gb,
            'traffic_used_gb': round(traffic_used_gb, 3),
            'subscription_url': getattr(subscription, 'subscription_url', None),
            'device_limit': getattr(subscription, 'device_limit', 1),
            'autopay_enabled': bool(getattr(subscription, 'autopay_enabled', False)),
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
