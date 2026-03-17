"""Mobile subscription management endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.crud.user import get_user_by_telegram_id
from app.mobile.schemas.subscription import (
    AutopayRequest,
    AutopayResponse,
    BalanceResponse,
    BalanceTopupRequest,
    BalanceTopupResponse,
    BuyResponse,
    CalcResponse,
    SubscriptionBuyRequest,
    SubscriptionOptionsResponse,
    SubscriptionSelectionRequest,
    SubscriptionUpgradeRequest,
    UpgradeCalcResponse,
    UpgradeResponse,
)


logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_db_user(x_telegram_id: int) -> tuple[Any, Any, Any]:
    """Return (user, db, engine).  Caller must dispose the engine."""
    db_url = settings.get_database_url()
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

    db = async_session()
    try:
        user = await get_user_by_telegram_id(db, x_telegram_id)
    except Exception as exc:
        await db.close()
        await engine.dispose()
        raise exc

    if not user:
        await db.close()
        await engine.dispose()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Пользователь не найден')

    if user.status != 'active':
        await db.close()
        await engine.dispose()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Учётная запись заблокирована')

    return user, db, engine


def _serialize_subscription(sub: Any) -> dict[str, Any] | None:
    if sub is None:
        return None
    from datetime import UTC

    end_date = getattr(sub, 'end_date', None)
    expire_ts: int | None = None
    if end_date is not None:
        try:
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=UTC)
            expire_ts = int(end_date.timestamp())
        except (AttributeError, ValueError, OSError):
            expire_ts = None

    traffic_limit_gb = getattr(sub, 'traffic_limit_gb', 0) or 0
    purchased_traffic_gb = getattr(sub, 'purchased_traffic_gb', 0) or 0

    return {
        'status': getattr(sub, 'status', 'unknown'),
        'is_trial': bool(getattr(sub, 'is_trial', False)),
        'expire_at': expire_ts,
        'traffic_limit_gb': traffic_limit_gb + purchased_traffic_gb,
        'traffic_used_gb': round(float(getattr(sub, 'traffic_used_gb', 0.0) or 0.0), 3),
        'subscription_url': getattr(sub, 'subscription_url', None),
        'device_limit': getattr(sub, 'device_limit', 1),
        'autopay_enabled': bool(getattr(sub, 'autopay_enabled', False)),
        'connected_squads': list(getattr(sub, 'connected_squads', []) or []),
    }


# ---------------------------------------------------------------------------
# GET /mobile/v1/subscription/options
# ---------------------------------------------------------------------------


@router.get(
    '/subscription/options',
    response_model=SubscriptionOptionsResponse,
    summary='Получить параметры конфигурации подписки',
    tags=['mobile'],
)
async def get_subscription_options(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> SubscriptionOptionsResponse:
    """Return available subscription builder options for the current user."""
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        await db.refresh(user, ['subscription'])

        from app.services.subscription_purchase_service import MiniAppSubscriptionPurchaseService

        service = MiniAppSubscriptionPurchaseService()
        context = await service.build_options(db, user)

        subscription = getattr(user, 'subscription', None)

        # Build a serialisable representation of the context
        context_payload: dict[str, Any] = {
            'periods': [p.to_payload() for p in context.periods],
            'balance_kopeks': context.balance_kopeks,
            'balance_rub': round(context.balance_kopeks / 100, 2),
            'currency': context.currency,
        }

        if subscription:
            context_payload['current_subscription'] = _serialize_subscription(subscription)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error building subscription options', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при получении параметров подписки',
        ) from exc
    finally:
        await db.close()
        await engine.dispose()

    return SubscriptionOptionsResponse(
        has_subscription=subscription is not None,
        context=context_payload,
    )


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/calc
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/calc',
    response_model=CalcResponse,
    summary='Рассчитать стоимость подписки',
    tags=['mobile'],
)
async def calc_subscription_price(
    payload: SubscriptionSelectionRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> CalcResponse:
    """Calculate the price for the given subscription configuration."""
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        await db.refresh(user, ['subscription'])

        from app.services.subscription_purchase_service import MiniAppSubscriptionPurchaseService

        service = MiniAppSubscriptionPurchaseService()
        context = await service.build_options(db, user)

        selection_dict: dict[str, Any] = {'period_id': payload.period_id}
        if payload.traffic_value is not None:
            selection_dict['traffic_value'] = payload.traffic_value
        if payload.devices is not None:
            selection_dict['devices'] = payload.devices
        if payload.servers is not None:
            selection_dict['servers'] = payload.servers

        selection = service.parse_selection(context, selection_dict)
        pricing = await service.calculate_pricing(db, context, selection)
        preview = service.build_preview_payload(context, pricing)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error calculating subscription price', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await db.close()
        await engine.dispose()

    return CalcResponse(
        total_kopeks=pricing.final_total,
        total_rub=round(pricing.final_total / 100, 2),
        details=pricing.details,
        preview=preview,
    )


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/buy
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/buy',
    response_model=BuyResponse,
    summary='Купить подписку',
    tags=['mobile'],
)
async def buy_subscription(
    payload: SubscriptionBuyRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> BuyResponse:
    """
    Purchase a subscription.

    * If the user has enough balance, the subscription is activated immediately.
    * If the balance is insufficient, a YooKassa payment is created and the
      confirmation URL is returned so the app can open it in a browser.
    """
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        await db.refresh(user, ['subscription'])

        from app.services.subscription_purchase_service import (
            MiniAppSubscriptionPurchaseService,
            PurchaseBalanceError,
            PurchaseValidationError,
        )

        service = MiniAppSubscriptionPurchaseService()
        context = await service.build_options(db, user)

        selection_dict: dict[str, Any] = {'period_id': payload.period_id}
        if payload.traffic_value is not None:
            selection_dict['traffic_value'] = payload.traffic_value
        if payload.devices is not None:
            selection_dict['devices'] = payload.devices
        if payload.servers is not None:
            selection_dict['servers'] = payload.servers

        selection = service.parse_selection(context, selection_dict)
        pricing = await service.calculate_pricing(db, context, selection)

        balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)

        if balance_kopeks >= pricing.final_total:
            # Sufficient balance – purchase immediately
            result = await service.submit_purchase(db, context, pricing)
            subscription = result.get('subscription')
            return BuyResponse(
                status='success',
                message='Подписка активирована',
                subscription=_serialize_subscription(subscription),
            )

        # Insufficient balance – create a YooKassa topup payment
        if not settings.is_yookassa_enabled():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail='Недостаточно средств на балансе. Пополните баланс в боте.',
            )

        from app.services.payment_service import PaymentService

        payment_service = PaymentService()
        amount_kopeks = pricing.final_total
        description = f'Подписка на {selection.period.days} дней'

        payment_result = await payment_service.create_yookassa_payment(
            db=db,
            user_id=user.id,
            amount_kopeks=amount_kopeks,
            description=description,
            metadata={
                'type': 'mobile_subscription_topup',
                'period_id': payload.period_id,
                'traffic_value': str(payload.traffic_value or selection.traffic_value),
                'devices': str(payload.devices or selection.devices),
                'servers': ','.join(payload.servers or selection.servers),
            },
        )

        if not payment_result or not payment_result.get('confirmation_url'):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Не удалось создать платёж',
            )

        # Save a cart so the auto-purchase service can activate the subscription
        # immediately after the payment is confirmed and the balance is credited.
        try:
            from app.services.user_cart_service import user_cart_service

            period_days = selection.period.days
            cart_data: dict[str, Any] = {
                'period_days': period_days,
                'traffic_gb': payload.traffic_value or selection.traffic_value,
                'devices': payload.devices or selection.devices,
                'countries': list(payload.servers or selection.servers),
                'source': 'mobile',
            }
            await user_cart_service.save_user_cart(user.id, cart_data)
        except Exception as cart_err:
            logger.warning('mobile buy: failed to save cart for auto-purchase', error=cart_err)

        return BuyResponse(
            status='payment_required',
            message='Пополните баланс для активации подписки',
            payment_url=payment_result['confirmation_url'],
            amount_kopeks=amount_kopeks,
        )

    except (PurchaseValidationError, PurchaseBalanceError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error buying subscription', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при покупке подписки',
        ) from exc
    finally:
        await db.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/upgrade
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/upgrade',
    response_model=UpgradeResponse,
    summary='Улучшить существующую подписку',
    tags=['mobile'],
)
async def upgrade_subscription(
    payload: SubscriptionUpgradeRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> UpgradeResponse:
    """
    Upgrade (extend / add traffic / add devices) an existing subscription.

    At least one of period_id, traffic_add, or devices_add must be provided.
    When only traffic_add / devices_add are provided (no period_id), the
    subscription duration is NOT extended – only the requested parameters change.
    Deducts cost from balance; creates YooKassa payment if balance is insufficient.
    """
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        await db.refresh(user, ['subscription'])
        subscription = getattr(user, 'subscription', None)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Активная подписка не найдена',
            )

        if not payload.period_id and payload.traffic_add is None and payload.devices_add is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Укажите хотя бы один параметр улучшения',
            )

        from app.database.crud.user import subtract_user_balance
        from app.services.subscription_purchase_service import (
            MiniAppSubscriptionPurchaseService,
            PurchaseBalanceError,
            PurchaseValidationError,
        )

        service = MiniAppSubscriptionPurchaseService()
        context = await service.build_options(db, user)

        # Whether the user explicitly requested a period extension.
        # When False (traffic/device-only upgrade), the subscription duration
        # must not be changed.
        extend_period = bool(payload.period_id)

        # Determine the period – used for pricing even when not extending
        period_id = payload.period_id
        if not period_id and context.periods:
            period_id = context.periods[0].id

        if not period_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Период не определён')

        # Build selection keeping current values as defaults
        current_traffic = getattr(subscription, 'traffic_limit_gb', 0) or 0
        current_devices = getattr(subscription, 'device_limit', 1)
        current_servers = list(getattr(subscription, 'connected_squads', []) or [])

        new_traffic = current_traffic + (payload.traffic_add or 0)
        new_devices = current_devices + (payload.devices_add or 0)
        new_servers = payload.servers if payload.servers is not None else current_servers

        selection_dict: dict[str, Any] = {
            'period_id': period_id,
            'traffic_value': new_traffic if new_traffic > 0 else current_traffic,
            'devices': new_devices,
            'servers': new_servers,
        }

        selection = service.parse_selection(context, selection_dict)
        pricing = await service.calculate_pricing(db, context, selection)

        balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)

        if extend_period:
            # Full renewal (± traffic/devices): delegate to submit_purchase which
            # also handles the subscription end_date extension.
            if balance_kopeks >= pricing.final_total:
                result = await service.submit_purchase(db, context, pricing)
                sub = result.get('subscription')
                return UpgradeResponse(
                    status='success',
                    message='Подписка улучшена',
                    subscription=_serialize_subscription(sub),
                )
        else:
            # Traffic / device only upgrade: deduct balance and update fields
            # directly – subscription end_date must NOT change.
            if balance_kopeks >= pricing.final_total:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                success = await subtract_user_balance(
                    db,
                    user,
                    pricing.final_total,
                    'Апгрейд подписки (трафик/устройства)',
                    consume_promo_offer=pricing.promo_discount_value > 0,
                )
                if not success:
                    raise PurchaseBalanceError('Недостаточно средств на балансе')
                if payload.traffic_add:
                    subscription.traffic_limit_gb = new_traffic
                if payload.devices_add:
                    subscription.device_limit = new_devices
                subscription.updated_at = now
                await db.commit()
                await db.refresh(subscription)
                return UpgradeResponse(
                    status='success',
                    message='Подписка улучшена',
                    subscription=_serialize_subscription(subscription),
                )

        # Insufficient balance – create YooKassa payment
        if not settings.is_yookassa_enabled():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail='Недостаточно средств на балансе. Пополните баланс в боте.',
            )

        from app.services.payment_service import PaymentService

        payment_service = PaymentService()
        amount_kopeks = pricing.final_total
        description = (
            f'Улучшение подписки на {selection.period.days} дней'
            if extend_period
            else 'Апгрейд подписки (трафик/устройства)'
        )

        payment_result = await payment_service.create_yookassa_payment(
            db=db,
            user_id=user.id,
            amount_kopeks=amount_kopeks,
            description=description,
            metadata={
                'type': 'mobile_subscription_upgrade_topup',
                'period_id': period_id,
            },
        )

        if not payment_result or not payment_result.get('confirmation_url'):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Не удалось создать платёж',
            )

        # Save a cart so the auto-purchase service can activate the upgrade
        # immediately after the payment is confirmed and the balance is credited.
        try:
            from app.services.user_cart_service import user_cart_service

            cart_data: dict[str, Any] = {
                'traffic_gb': selection.traffic_value,
                'devices': selection.devices,
                'countries': list(selection.servers),
                'source': 'mobile',
            }
            # Only include period_days when the user explicitly requested extension
            if extend_period:
                cart_data['period_days'] = selection.period.days
            await user_cart_service.save_user_cart(user.id, cart_data)
        except Exception as cart_err:
            logger.warning('mobile upgrade: failed to save cart for auto-purchase', error=cart_err)

        return UpgradeResponse(
            status='payment_required',
            message='Пополните баланс для улучшения подписки',
            payment_url=payment_result['confirmation_url'],
            amount_kopeks=amount_kopeks,
        )

    except (PurchaseValidationError, PurchaseBalanceError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error upgrading subscription', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при улучшении подписки',
        ) from exc
    finally:
        await db.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/upgrade/calc
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/upgrade/calc',
    response_model=UpgradeCalcResponse,
    summary='Рассчитать стоимость улучшения подписки',
    tags=['mobile'],
)
async def calc_upgrade_price(
    payload: SubscriptionUpgradeRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> UpgradeCalcResponse:
    """
    Calculate the cost of upgrading an existing subscription without applying it.
    Uses the same pricing logic as the upgrade endpoint.
    Returns amount_kopeks and amount_rub without making any changes.
    """
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        await db.refresh(user, ['subscription'])
        subscription = getattr(user, 'subscription', None)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Активная подписка не найдена',
            )

        from app.services.subscription_purchase_service import (
            MiniAppSubscriptionPurchaseService,
            PurchaseValidationError,
        )

        service = MiniAppSubscriptionPurchaseService()
        context = await service.build_options(db, user)

        period_id = payload.period_id
        if not period_id and context.periods:
            period_id = context.periods[0].id

        if not period_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Период не определён')

        current_traffic = getattr(subscription, 'traffic_limit_gb', 0) or 0
        current_devices = getattr(subscription, 'device_limit', 1)
        current_servers = list(getattr(subscription, 'connected_squads', []) or [])

        new_traffic = current_traffic + (payload.traffic_add or 0)
        new_devices = current_devices + (payload.devices_add or 0)
        new_servers = payload.servers if payload.servers is not None else current_servers

        selection_dict: dict[str, Any] = {
            'period_id': period_id,
            'traffic_value': new_traffic if new_traffic > 0 else current_traffic,
            'devices': new_devices,
            'servers': new_servers,
        }

        selection = service.parse_selection(context, selection_dict)
        pricing = await service.calculate_pricing(db, context, selection)

        return UpgradeCalcResponse(
            amount_kopeks=pricing.final_total,
            amount_rub=round(pricing.final_total / 100, 2),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error calculating upgrade price', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await db.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# GET /mobile/v1/balance
# ---------------------------------------------------------------------------


@router.get(
    '/balance',
    response_model=BalanceResponse,
    summary='Получить баланс пользователя',
    tags=['mobile'],
)
async def get_balance(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> BalanceResponse:
    """Return the current account balance for the authenticated user."""
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)
        currency = (getattr(user, 'balance_currency', None) or 'RUB').upper()
    finally:
        await db.close()
        await engine.dispose()

    return BalanceResponse(
        balance_kopeks=balance_kopeks,
        balance_rub=round(balance_kopeks / 100, 2),
        currency=currency,
    )


# ---------------------------------------------------------------------------
# POST /mobile/v1/balance/topup
# ---------------------------------------------------------------------------


@router.post(
    '/balance/topup',
    response_model=BalanceTopupResponse,
    summary='Пополнить баланс',
    tags=['mobile'],
)
async def topup_balance(
    payload: BalanceTopupRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> BalanceTopupResponse:
    """
    Create a YooKassa payment to top up the user's account balance.

    Returns a confirmation URL that the app should open in an external browser.
    After a successful payment, the backend webhook will credit the balance.
    """
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        if not settings.is_yookassa_enabled():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail='Онлайн-оплата недоступна. Пополните баланс через бот.',
            )

        from app.services.payment_service import PaymentService

        amount_kopeks = payload.amount_kopeks
        description = f'Пополнение баланса на {round(amount_kopeks / 100, 2)} ₽'

        payment_service = PaymentService()
        payment_result = await payment_service.create_yookassa_payment(
            db=db,
            user_id=user.id,
            amount_kopeks=amount_kopeks,
            description=description,
            metadata={
                'type': 'mobile_balance_topup',
                'telegram_id': str(x_telegram_id),
            },
        )

        if not payment_result or not payment_result.get('confirmation_url'):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Не удалось создать платёж',
            )

        return BalanceTopupResponse(
            status='payment_required',
            payment_url=payment_result['confirmation_url'],
            message='Перейдите по ссылке для оплаты',
            amount_kopeks=amount_kopeks,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error creating balance topup payment', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при создании платежа',
        ) from exc
    finally:
        await db.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# PUT /mobile/v1/subscription/autopay
# ---------------------------------------------------------------------------


@router.put(
    '/subscription/autopay',
    response_model=AutopayResponse,
    summary='Включить/отключить автопродление',
    tags=['mobile'],
)
async def set_autopay(
    payload: AutopayRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> AutopayResponse:
    """Enable or disable automatic subscription renewal from account balance."""
    user, db, engine = await _get_db_user(x_telegram_id)

    try:
        await db.refresh(user, ['subscription'])
        subscription = getattr(user, 'subscription', None)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Подписка не найдена',
            )

        subscription.autopay_enabled = payload.enabled
        await db.commit()

        enabled = bool(subscription.autopay_enabled)
        message = 'Автопродление включено' if enabled else 'Автопродление отключено'

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error updating autopay', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обновлении настроек автопродления',
        ) from exc
    finally:
        await db.close()
        await engine.dispose()

    return AutopayResponse(autopay_enabled=enabled, message=message)
