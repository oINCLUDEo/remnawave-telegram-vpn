"""Mobile subscription management endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import PERIOD_PRICES, settings
from app.database.crud.user import get_user_by_telegram_id
from app.mobile.schemas.subscription import (
    AutopayRequest,
    AutopayResponse,
    BalanceResponse,
    SubBuyRequest,
    SubBuyResponse,
    SubCalcRequest,
    SubCalcResponse,
    SubUpgradeRequest,
    SubUpgradeResponse,
)


logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_session(db_url: str):
    engine = create_async_engine(db_url, echo=False)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
    return engine, session_factory


async def _get_user_or_raise(session_factory, telegram_id: int):
    async with session_factory() as db:
        user = await get_user_by_telegram_id(db, telegram_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Пользователь не найден')
        if user.status != 'active':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Учётная запись заблокирована')
        await db.refresh(user, ['subscription'])
        return user, db


def _calc_price_kopeks(days: int, traffic_gb: int, devices: int) -> int:
    """Calculate subscription price in kopeks using current PERIOD_PRICES."""
    base = PERIOD_PRICES.get(days, 0)
    if not base:
        # Interpolate linearly from the nearest available period
        available = sorted(PERIOD_PRICES.keys())
        if available:
            # Find closest period
            closest = min(available, key=lambda d: abs(d - days))
            closest_price = PERIOD_PRICES[closest]
            base = round(closest_price * days / closest)
        else:
            base = 0

    traffic_price = settings.get_traffic_price(traffic_gb)

    # Device multiplier: first device included, each additional device costs
    # same share as per-period base price × 0.3 per extra device (heuristic).
    device_extra = max(0, devices - 1) * round(base * 0.3) if base else 0

    return base + traffic_price + device_extra


# ---------------------------------------------------------------------------
# POST /subscription/calc
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/calc',
    response_model=SubCalcResponse,
    summary='Рассчитать стоимость подписки',
    tags=['mobile'],
)
async def calc_subscription(
    body: SubCalcRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> SubCalcResponse:
    """Return price for the requested subscription configuration."""
    price_kopeks = _calc_price_kopeks(body.days, body.traffic_gb, body.devices)
    return SubCalcResponse(
        price_kopeks=price_kopeks,
        price_rub=round(price_kopeks / 100, 2),
    )


# ---------------------------------------------------------------------------
# POST /subscription/buy
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/buy',
    response_model=SubBuyResponse,
    summary='Купить подписку',
    tags=['mobile'],
)
async def buy_subscription(
    body: SubBuyRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> SubBuyResponse:
    """Initiate a subscription purchase."""
    try:
        db_url = settings.get_database_url()
        engine, session_factory = _make_db_session(db_url)

        async with session_factory() as db:
            user = await get_user_by_telegram_id(db, x_telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail='Пользователь не найден')
            if user.status != 'active':
                raise HTTPException(status_code=403, detail='Учётная запись заблокирована')

            price_kopeks = _calc_price_kopeks(body.days, body.traffic_gb, body.devices)

            if body.payment_method == 'balance':
                if user.balance_kopeks < price_kopeks:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail='Недостаточно средств на балансе',
                    )
                # Deduct from balance
                user.balance_kopeks -= price_kopeks
                await db.commit()
                await engine.dispose()
                return SubBuyResponse(
                    paid_from_balance=True,
                    message='Подписка успешно оплачена с баланса',
                )

            # YooKassa payment
            await engine.dispose()
            if not settings.is_yookassa_enabled():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail='Оплата временно недоступна',
                )

            try:
                from app.services.yookassa_service import YooKassaService

                yk = YooKassaService()
                description = (
                    f'Подписка {body.days} дн. / '
                    f'{body.traffic_gb if body.traffic_gb else "∞"} ГБ / '
                    f'{body.devices} уст.'
                )
                payment = await yk.create_payment(
                    amount_kopeks=price_kopeks,
                    description=description,
                    metadata={
                        'telegram_id': x_telegram_id,
                        'days': body.days,
                        'traffic_gb': body.traffic_gb,
                        'devices': body.devices,
                        'source': 'mobile_app',
                    },
                    return_url=body.return_url or 'https://t.me',
                )
                payment_url = (
                    payment.get('confirmation', {}).get('confirmation_url')
                    if isinstance(payment, dict)
                    else getattr(getattr(payment, 'confirmation', None), 'confirmation_url', None)
                )
                if not payment_url:
                    raise HTTPException(status_code=502, detail='Не удалось создать платёж')

                return SubBuyResponse(
                    payment_url=payment_url,
                    message='Перейдите по ссылке для оплаты',
                )
            except HTTPException:
                raise
            except Exception as exc:
                logger.error('YooKassa payment creation failed', error=exc)
                raise HTTPException(status_code=502, detail='Ошибка создания платежа') from exc

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('buy_subscription error', error=exc)
        raise HTTPException(status_code=502, detail='Внутренняя ошибка') from exc


# ---------------------------------------------------------------------------
# POST /subscription/upgrade
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/upgrade',
    response_model=SubUpgradeResponse,
    summary='Улучшить подписку',
    tags=['mobile'],
)
async def upgrade_subscription(
    body: SubUpgradeRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> SubUpgradeResponse:
    """Upgrade an existing subscription (add traffic, devices, or extend duration)."""
    valid_actions = {'traffic', 'devices', 'days'}
    if body.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f'Неверный action. Допустимые: {valid_actions}')

    try:
        db_url = settings.get_database_url()
        engine, session_factory = _make_db_session(db_url)

        async with session_factory() as db:
            user = await get_user_by_telegram_id(db, x_telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail='Пользователь не найден')
            if user.status != 'active':
                raise HTTPException(status_code=403, detail='Учётная запись заблокирована')
            await db.refresh(user, ['subscription'])
            subscription = getattr(user, 'subscription', None)
            if not subscription:
                raise HTTPException(status_code=404, detail='Подписка не найдена')

            # Calculate upgrade price
            if body.action == 'traffic':
                price_kopeks = settings.get_traffic_price(body.value)
            elif body.action == 'devices':
                base_30 = PERIOD_PRICES.get(30, 0)
                price_kopeks = body.value * round(base_30 * 0.3) if base_30 else 0
            else:  # days
                price_kopeks = _calc_price_kopeks(
                    body.value,
                    getattr(subscription, 'traffic_limit_gb', 0) or 0,
                    getattr(subscription, 'device_limit', 1),
                )

            if body.payment_method == 'balance':
                if user.balance_kopeks < price_kopeks:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail='Недостаточно средств на балансе',
                    )
                user.balance_kopeks -= price_kopeks
                await db.commit()
                await engine.dispose()
                return SubUpgradeResponse(
                    price_kopeks=price_kopeks,
                    price_rub=round(price_kopeks / 100, 2),
                    paid_from_balance=True,
                    message='Улучшение применено',
                )

            await engine.dispose()
            if not settings.is_yookassa_enabled():
                raise HTTPException(status_code=503, detail='Оплата временно недоступна')

            try:
                from app.services.yookassa_service import YooKassaService

                yk = YooKassaService()
                action_labels = {'traffic': f'+{body.value} ГБ', 'devices': f'+{body.value} уст.', 'days': f'+{body.value} дн.'}
                payment = await yk.create_payment(
                    amount_kopeks=price_kopeks,
                    description=f'Улучшение подписки: {action_labels[body.action]}',
                    metadata={
                        'telegram_id': x_telegram_id,
                        'action': body.action,
                        'value': body.value,
                        'source': 'mobile_app_upgrade',
                    },
                    return_url='https://t.me',
                )
                payment_url = (
                    payment.get('confirmation', {}).get('confirmation_url')
                    if isinstance(payment, dict)
                    else getattr(getattr(payment, 'confirmation', None), 'confirmation_url', None)
                )
                if not payment_url:
                    raise HTTPException(status_code=502, detail='Не удалось создать платёж')
                return SubUpgradeResponse(
                    price_kopeks=price_kopeks,
                    price_rub=round(price_kopeks / 100, 2),
                    payment_url=payment_url,
                    message='Перейдите по ссылке для оплаты',
                )
            except HTTPException:
                raise
            except Exception as exc:
                logger.error('YooKassa upgrade payment creation failed', error=exc)
                raise HTTPException(status_code=502, detail='Ошибка создания платежа') from exc

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('upgrade_subscription error', error=exc)
        raise HTTPException(status_code=502, detail='Внутренняя ошибка') from exc


# ---------------------------------------------------------------------------
# GET /balance
# ---------------------------------------------------------------------------


@router.get(
    '/balance',
    response_model=BalanceResponse,
    summary='Баланс пользователя',
    tags=['mobile'],
)
async def get_balance(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> BalanceResponse:
    """Return user balance and autopay settings."""
    try:
        db_url = settings.get_database_url()
        engine, session_factory = _make_db_session(db_url)

        async with session_factory() as db:
            user = await get_user_by_telegram_id(db, x_telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail='Пользователь не найден')
            if user.status != 'active':
                raise HTTPException(status_code=403, detail='Учётная запись заблокирована')
            await db.refresh(user, ['subscription'])
            subscription = getattr(user, 'subscription', None)
            autopay = bool(getattr(subscription, 'autopay_enabled', False)) if subscription else False
            autopay_days = int(getattr(subscription, 'autopay_days_before', 3)) if subscription else 3
            balance_kopeks = int(user.balance_kopeks or 0)

        await engine.dispose()
        return BalanceResponse(
            balance_kopeks=balance_kopeks,
            balance_rub=round(balance_kopeks / 100, 2),
            autopay_enabled=autopay,
            autopay_days_before=autopay_days,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('get_balance error', error=exc)
        raise HTTPException(status_code=502, detail='Внутренняя ошибка') from exc


# ---------------------------------------------------------------------------
# PUT /subscription/autopay
# ---------------------------------------------------------------------------


@router.put(
    '/subscription/autopay',
    response_model=AutopayResponse,
    summary='Включить / отключить автопродление',
    tags=['mobile'],
)
async def set_autopay(
    body: AutopayRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> AutopayResponse:
    """Toggle auto-renewal for the user's subscription."""
    try:
        db_url = settings.get_database_url()
        engine, session_factory = _make_db_session(db_url)

        async with session_factory() as db:
            user = await get_user_by_telegram_id(db, x_telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail='Пользователь не найден')
            if user.status != 'active':
                raise HTTPException(status_code=403, detail='Учётная запись заблокирована')
            await db.refresh(user, ['subscription'])
            subscription = getattr(user, 'subscription', None)
            if not subscription:
                raise HTTPException(status_code=404, detail='Подписка не найдена')

            subscription.autopay_enabled = body.enabled
            await db.commit()

        await engine.dispose()
        label = 'включено' if body.enabled else 'отключено'
        return AutopayResponse(enabled=body.enabled, message=f'Автопродление {label}')

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('set_autopay error', error=exc)
        raise HTTPException(status_code=502, detail='Внутренняя ошибка') from exc
