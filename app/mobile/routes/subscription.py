"""Mobile subscription management endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_current_cabinet_user
from app.config import settings
from app.database.crud.tariff import get_tariff_by_id
from app.database.models import User
from app.mobile.schemas.subscription import (
    AutopayRequest,
    AutopayResponse,
    BalanceResponse,
    BalanceTopupRequest,
    BalanceTopupResponse,
    BuyResponse,
    CalcResponse,
    DeviceDeleteRequest,
    DevicesListResponse,
    DevicesResetResponse,
    SubscriptionBuyRequest,
    SubscriptionOptionsResponse,
    SubscriptionSelectionRequest,
    SubscriptionUpgradeRequest,
    TariffBuyRequest,
    TariffSwitchPreviewResponse,
    TariffSwitchRequest,
    TariffSwitchResponse,
    UpgradeCalcResponse,
    UpgradeResponse,
)
from app.services.pricing_engine import pricing_engine
from app.utils.pricing_utils import balance_covers_price


logger = structlog.get_logger(__name__)

router = APIRouter()

_MOBILE_SOURCE = 'Мобильное приложение'


# ---------------------------------------------------------------------------
# Admin notification helper
# ---------------------------------------------------------------------------


async def _notify_mobile_purchase(
    db: Any,
    user: Any,
    subscription: Any,
    *,
    period_days: int,
    amount_kopeks: int,
    purchase_type: str,
) -> None:
    """Send admin Telegram notification for a successful mobile purchase/renewal."""
    try:
        from aiogram import Bot

        from app.config import settings
        from app.services.admin_notification_service import AdminNotificationService

        if not (getattr(settings, 'ADMIN_NOTIFICATIONS_ENABLED', False) and settings.BOT_TOKEN):
            return
        bot = Bot(token=settings.BOT_TOKEN)
        try:
            ns = AdminNotificationService(bot)
            await ns.send_subscription_purchase_notification(
                db=db,
                user=user,
                subscription=subscription,
                transaction=None,
                period_days=period_days,
                amount_kopeks=amount_kopeks,
                purchase_type=purchase_type,
                source=_MOBILE_SOURCE,
            )
        finally:
            await bot.session.close()
    except Exception as e:
        logger.error('mobile: failed to send admin purchase notification', error=e)


async def _notify_mobile_upgrade(
    db: Any,
    user: Any,
    subscription: Any,
    *,
    update_type: str,
    old_value: Any,
    new_value: Any,
    price_kopeks: int,
) -> None:
    """Send admin Telegram notification for a successful mobile subscription upgrade."""
    try:
        from aiogram import Bot

        from app.config import settings
        from app.services.admin_notification_service import AdminNotificationService

        if not (getattr(settings, 'ADMIN_NOTIFICATIONS_ENABLED', False) and settings.BOT_TOKEN):
            return
        bot = Bot(token=settings.BOT_TOKEN)
        try:
            ns = AdminNotificationService(bot)
            await ns.send_subscription_update_notification(
                db=db,
                user=user,
                subscription=subscription,
                update_type=update_type,
                old_value=old_value,
                new_value=new_value,
                price_paid=price_kopeks,
                source=_MOBILE_SOURCE,
            )
        finally:
            await bot.session.close()
    except Exception as e:
        logger.error('mobile: failed to send admin upgrade notification', error=e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

    # Include plan name if the tariff relationship was already loaded (no lazy load).
    tariff = getattr(sub, 'tariff', None)
    plan_name: str | None = getattr(tariff, 'name', None) or None

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
        'plan_name': plan_name,
    }


async def _build_topup_info(db: AsyncSession, subscription: Any, user: Any) -> dict[str, Any]:
    """Mirror cabinet/miniapp top-up logic for both tariff and classic sales modes."""
    if not subscription:
        return {}

    info: dict[str, Any] = {
        'traffic_topup_enabled': False,
        'traffic_topup_packages': [],
        'max_topup_traffic_gb': None,
        'available_topup_gb': None,
    }

    is_tariff_mode = settings.is_tariffs_mode() and getattr(subscription, 'tariff_id', None)
    tariff = None

    if getattr(subscription, 'tariff_id', None):
        tariff = await get_tariff_by_id(db, subscription.tariff_id)

    if is_tariff_mode and tariff:
        max_topup_traffic_gb = getattr(tariff, 'max_topup_traffic_gb', 0) or 0
        current_subscription_traffic = subscription.traffic_limit_gb or 0
        available_topup_gb = None
        if max_topup_traffic_gb > 0:
            available_topup_gb = max(0, max_topup_traffic_gb - current_subscription_traffic)

        traffic_topup_enabled = getattr(tariff, 'traffic_topup_enabled', False) and tariff.traffic_limit_gb > 0
        traffic_topup_packages: list[dict[str, Any]] = []

        if traffic_topup_enabled and hasattr(tariff, 'get_traffic_topup_packages'):
            packages = tariff.get_traffic_topup_packages()
            for gb in sorted(packages.keys()):
                if available_topup_gb is not None and gb > available_topup_gb:
                    continue

                base_price = packages[gb]
                discounted_price, _discount_val, traffic_discount_pct = pricing_engine.calculate_traffic_discount(
                    base_price,
                    user,
                )
                if traffic_discount_pct > 0:
                    traffic_topup_packages.append(
                        {
                            'gb': gb,
                            'price_kopeks': discounted_price,
                            'price_label': settings.format_price(discounted_price),
                            'original_price_kopeks': base_price,
                            'original_price_label': settings.format_price(base_price),
                            'discount_percent': traffic_discount_pct,
                        }
                    )
                else:
                    traffic_topup_packages.append(
                        {
                            'gb': gb,
                            'price_kopeks': base_price,
                            'price_label': settings.format_price(base_price),
                        }
                    )

        if traffic_topup_enabled and not traffic_topup_packages and available_topup_gb == 0:
            traffic_topup_enabled = False

        info.update(
            {
                'traffic_topup_enabled': traffic_topup_enabled,
                'traffic_topup_packages': traffic_topup_packages,
                'max_topup_traffic_gb': max_topup_traffic_gb,
                'available_topup_gb': available_topup_gb,
            }
        )
        return info

    # Classic mode: use global settings (with optional tariff-level allow flag)
    if not settings.is_traffic_topup_enabled():
        return info

    if tariff and getattr(tariff, 'allow_traffic_topup', True) is False:
        return info

    packages = settings.get_traffic_topup_packages()
    traffic_topup_packages: list[dict[str, Any]] = []

    for pkg in packages:
        if not pkg.get('enabled', True):
            continue
        base_price = int(pkg.get('price', 0) or 0)
        if base_price <= 0:
            continue

        gb_value = int(pkg.get('gb', 0) or 0)
        discounted_price, _discount_val, traffic_discount_pct = pricing_engine.calculate_traffic_discount(
            base_price,
            user,
        )

        package_payload: dict[str, Any] = {
            'gb': gb_value,
            'price_kopeks': discounted_price if traffic_discount_pct > 0 else base_price,
            'price_label': settings.format_price(discounted_price if traffic_discount_pct > 0 else base_price),
        }
        if traffic_discount_pct > 0:
            package_payload.update(
                {
                    'original_price_kopeks': base_price,
                    'original_price_label': settings.format_price(base_price),
                    'discount_percent': traffic_discount_pct,
                }
            )

        traffic_topup_packages.append(package_payload)

    if traffic_topup_packages:
        info.update(
            {
                'traffic_topup_enabled': True,
                'traffic_topup_packages': traffic_topup_packages,
            }
        )

    return info


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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> SubscriptionOptionsResponse:
    """Return available subscription builder options for the current user."""
    try:
        await db.refresh(user, ['subscriptions'])

        from app.services.subscription_purchase_service import MiniAppSubscriptionPurchaseService

        service = MiniAppSubscriptionPurchaseService()
        context = await service.build_options(db, user)

        subscription = getattr(user, 'subscription', None)
        # Load tariff relationship so plan_name is available in _serialize_subscription.
        if subscription is not None and getattr(subscription, 'tariff_id', None):
            await db.refresh(subscription, ['tariff'])

        # Build a serialisable representation of the context
        context_payload: dict[str, Any] = {
            'periods': [p.to_payload() for p in context.periods],
            'balance_kopeks': context.balance_kopeks,
            'balance_rub': round(context.balance_kopeks / 100, 2),
            'currency': context.currency,
        }

        if subscription:
            context_payload['current_subscription'] = _serialize_subscription(subscription)
            # Provide top-up options consistent with cabinet/miniapp
            topup_info = await _build_topup_info(db, subscription, user)
            if topup_info:
                context_payload.update(topup_info)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error building subscription options', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при получении параметров подписки',
        ) from exc

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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> CalcResponse:
    """Calculate the price for the given subscription configuration."""
    try:
        await db.refresh(user, ['subscriptions'])

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
        logger.error('Error calculating subscription price', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> BuyResponse:
    """
    Purchase a subscription.

    * If the user has enough balance, the subscription is activated immediately.
    * If the balance is insufficient, a YooKassa payment is created and the
      confirmation URL is returned so the app can open it in a browser.
    """
    try:
        await db.refresh(user, ['subscriptions'])

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

        if payload.use_balance and balance_covers_price(balance_kopeks, pricing.final_total):
            # Sufficient balance – purchase immediately
            result = await service.submit_purchase(db, context, pricing)
            subscription = result.get('subscription')

            # Admin notification
            await _notify_mobile_purchase(
                db, user, subscription,
                period_days=selection.period.days,
                amount_kopeks=pricing.final_total,
                purchase_type='renewal' if user.has_had_paid_subscription else 'first_purchase',
            )

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
        logger.error('Error buying subscription', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при покупке подписки',
        ) from exc


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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> UpgradeResponse:
    """
    Upgrade an existing subscription by adding devices or traffic.

    Only one of traffic_add or devices_add should be provided per call.
    Uses the same incremental pricing as the Telegram bot (not a full subscription reprice).
    Subscription duration is NEVER extended here — only the requested parameter changes.
    Deducts cost from balance; returns payment_required if balance is insufficient.
    """
    try:
        await db.refresh(user, ['subscriptions'])
        subscription = getattr(user, 'subscription', None)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Активная подписка не найдена',
            )

        if payload.traffic_add is None and payload.devices_add is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Укажите хотя бы один параметр улучшения: traffic_add или devices_add',
            )

        from app.database.crud.subscription import add_subscription_traffic
        from app.database.crud.transaction import create_transaction
        from app.database.crud.user import subtract_user_balance
        from app.database.models import TransactionType
        from app.utils.pricing_utils import calculate_prorated_price

        # Fetch tariff if present
        tariff = None
        if getattr(subscription, 'tariff_id', None):
            from app.database.crud.tariff import get_tariff_by_id

            tariff = await get_tariff_by_id(db, subscription.tariff_id)

        price = 0
        description = ''

        if payload.devices_add and payload.devices_add > 0:
            # ------------------------------------------------------------------
            # Device upgrade – same logic as bot's confirm_change_devices
            # ------------------------------------------------------------------
            if tariff:
                tariff_device_price = getattr(tariff, 'device_price_kopeks', None)
                if not tariff_device_price or tariff_device_price <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Изменение устройств недоступно для вашего тарифа',
                    )
                price_per_device = tariff_device_price
            else:
                if not settings.is_devices_selection_enabled():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Изменение количества устройств недоступно',
                    )
                price_per_device = settings.PRICE_PER_DEVICE

            current_devices = getattr(subscription, 'device_limit', 1)
            new_devices = current_devices + payload.devices_add

            if settings.MAX_DEVICES_LIMIT > 0 and new_devices > settings.MAX_DEVICES_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Превышен максимальный лимит устройств ({settings.MAX_DEVICES_LIMIT})',
                )

            # Chargeable devices: only above DEFAULT_DEVICE_LIMIT (free tier) unless tariff
            if tariff:
                chargeable = payload.devices_add
            else:
                free_remaining = max(0, settings.DEFAULT_DEVICE_LIMIT - current_devices)
                chargeable = max(0, payload.devices_add - free_remaining)

            if chargeable > 0:
                monthly_price = chargeable * price_per_device
                price, _ = calculate_prorated_price(monthly_price, subscription.end_date)

            description = f'Добавление {payload.devices_add} устройств (новый лимит: {new_devices})'

        elif payload.traffic_add and payload.traffic_add > 0:
            # ------------------------------------------------------------------
            # Traffic upgrade – same logic as bot's add_traffic
            # ------------------------------------------------------------------
            if tariff:
                if not tariff.can_topup_traffic():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='На вашем тарифе докупка трафика недоступна',
                    )
                base_price = tariff.get_traffic_topup_price(payload.traffic_add) or 0
                # Tariff price is already per-purchase (no prorating)
                price = base_price
            else:
                if settings.is_traffic_topup_blocked():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='В текущем режиме трафик фиксированный',
                    )
                base_price = settings.get_traffic_topup_price(payload.traffic_add)
                if base_price == 0 and payload.traffic_add != 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Цена для этого пакета трафика не настроена',
                    )
                price, _ = calculate_prorated_price(base_price, subscription.end_date)

            description = f'Добавление {payload.traffic_add} ГБ трафика'

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Значения должны быть положительными',
            )

        balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)

        if payload.use_balance and balance_covers_price(balance_kopeks, price):
            # Deduct balance
            success = await subtract_user_balance(db, user, price, description)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail='Недостаточно средств на балансе',
                )

            # Apply the upgrade
            if payload.devices_add and payload.devices_add > 0:
                current_devices = getattr(subscription, 'device_limit', 1)
                subscription.device_limit = current_devices + payload.devices_add
                from datetime import UTC, datetime

                subscription.updated_at = datetime.now(UTC)
                await db.commit()
                await db.refresh(subscription)

                # Sync with Remnawave
                try:
                    from app.services.subscription_service import SubscriptionService

                    await SubscriptionService().update_remnawave_user(db, subscription)
                except Exception as sync_err:
                    logger.warning('mobile upgrade: failed to sync remnawave after device add', error=sync_err)

            elif payload.traffic_add and payload.traffic_add > 0:
                await add_subscription_traffic(db, subscription, payload.traffic_add)
                await db.refresh(subscription)

                # Sync with Remnawave
                try:
                    from app.services.subscription_service import SubscriptionService

                    await SubscriptionService().update_remnawave_user(db, subscription)
                except Exception as sync_err:
                    logger.warning('mobile upgrade: failed to sync remnawave after traffic add', error=sync_err)

            # Create transaction record (so it appears in bot history)
            if price > 0:
                await create_transaction(
                    db=db,
                    user_id=user.id,
                    type=TransactionType.SUBSCRIPTION_PAYMENT,
                    amount_kopeks=price,
                    description=description,
                )

            await db.refresh(user)

            # Admin notification
            if payload.devices_add and payload.devices_add > 0:
                _old_dev = current_devices
                _new_dev = current_devices + payload.devices_add
                await _notify_mobile_upgrade(
                    db, user, subscription,
                    update_type='devices',
                    old_value=_old_dev,
                    new_value=_new_dev,
                    price_kopeks=price,
                )
            elif payload.traffic_add and payload.traffic_add > 0:
                _old_tr = getattr(subscription, 'traffic_limit_gb', 0)
                _new_tr = _old_tr + payload.traffic_add
                await _notify_mobile_upgrade(
                    db, user, subscription,
                    update_type='traffic',
                    old_value=_old_tr,
                    new_value=_new_tr,
                    price_kopeks=price,
                )

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
        payment_result = await payment_service.create_yookassa_payment(
            db=db,
            user_id=user.id,
            amount_kopeks=price,
            description=description,
            metadata={
                'type': 'mobile_subscription_upgrade_topup',
                'traffic_add': payload.traffic_add,
                'devices_add': payload.devices_add,
            },
        )

        if not payment_result or not payment_result.get('confirmation_url'):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Не удалось создать платёж',
            )

        # Save cart so auto-purchase activates upgrade after payment
        try:
            from app.services.user_cart_service import user_cart_service

            cart_data: dict[str, Any] = {'source': 'mobile'}
            if payload.devices_add:
                cart_data['cart_mode'] = 'add_devices'
                cart_data['devices_to_add'] = payload.devices_add
                cart_data['price_kopeks'] = price
            elif payload.traffic_add:
                cart_data['cart_mode'] = 'add_traffic'
                cart_data['subscription_id'] = subscription.id
                cart_data['traffic_gb'] = payload.traffic_add
                cart_data['price_kopeks'] = price
            await user_cart_service.save_user_cart(user.id, cart_data)
        except Exception as cart_err:
            logger.warning('mobile upgrade: failed to save cart', error=cart_err)

        return UpgradeResponse(
            status='payment_required',
            message='Пополните баланс для улучшения подписки',
            payment_url=payment_result['confirmation_url'],
            amount_kopeks=price,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error upgrading subscription', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при улучшении подписки',
        ) from exc


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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> UpgradeCalcResponse:
    """
    Calculate the incremental cost of adding devices or traffic to an existing
    subscription.  Uses the same pricing as the bot (prorated, not a full reprice).
    Returns amount_kopeks and amount_rub without making any changes.
    """
    try:
        await db.refresh(user, ['subscriptions'])
        subscription = getattr(user, 'subscription', None)

        if subscription is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Активная подписка не найдена',
            )

        if payload.traffic_add is None and payload.devices_add is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Укажите traffic_add или devices_add',
            )

        from app.utils.pricing_utils import calculate_prorated_price

        # Fetch tariff if present
        tariff = None
        if getattr(subscription, 'tariff_id', None):
            from app.database.crud.tariff import get_tariff_by_id

            tariff = await get_tariff_by_id(db, subscription.tariff_id)

        price = 0

        if payload.devices_add and payload.devices_add > 0:
            if tariff:
                tariff_device_price = getattr(tariff, 'device_price_kopeks', None)
                if not tariff_device_price or tariff_device_price <= 0:
                    return UpgradeCalcResponse(amount_kopeks=0, amount_rub=0)
                price_per_device = tariff_device_price
                chargeable = payload.devices_add
            else:
                price_per_device = settings.PRICE_PER_DEVICE
                current_devices = getattr(subscription, 'device_limit', 1)
                free_remaining = max(0, settings.DEFAULT_DEVICE_LIMIT - current_devices)
                chargeable = max(0, payload.devices_add - free_remaining)

            if chargeable > 0:
                monthly_price = chargeable * price_per_device
                price, _ = calculate_prorated_price(monthly_price, subscription.end_date)

        elif payload.traffic_add and payload.traffic_add > 0:
            if tariff:
                if not tariff.can_topup_traffic():
                    return UpgradeCalcResponse(amount_kopeks=0, amount_rub=0)
                price = tariff.get_traffic_topup_price(payload.traffic_add) or 0
            else:
                base_price = settings.get_traffic_topup_price(payload.traffic_add)
                price, _ = calculate_prorated_price(base_price, subscription.end_date)

        return UpgradeCalcResponse(
            amount_kopeks=price,
            amount_rub=round(price / 100, 2),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error calculating upgrade price', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/buy-tariff
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/buy-tariff',
    response_model=BuyResponse,
    summary='Купить конкретный тариф',
    tags=['mobile'],
)
async def buy_tariff(
    payload: TariffBuyRequest,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> BuyResponse:
    """
    Purchase a specific tariff for the given number of days.

    Works in tariffs mode.  Uses the same pricing engine as the cabinet
    ``/subscription/purchase-tariff`` endpoint.
    """
    if not settings.is_tariffs_mode():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Tariffs mode is not enabled. Use /subscription/buy instead.',
        )

    try:
        from app.database.crud.tariff import get_tariff_by_id
        from app.database.crud.user import lock_user_for_pricing
        from app.services.pricing_engine import pricing_engine

        tariff = await get_tariff_by_id(db, payload.tariff_id)
        if not tariff or not tariff.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Тариф не найден или неактивен',
            )

        # Lock user row to prevent TOCTOU races on promo-offer consumption
        user = await lock_user_for_pricing(db, user.id)

        # Promo-group availability check
        promo_group = (
            user.get_primary_promo_group()
            if hasattr(user, 'get_primary_promo_group')
            else None
        )
        if promo_group is None:
            promo_group = getattr(user, 'promo_group', None)
        promo_group_id = promo_group.id if promo_group else None
        if not tariff.is_available_for_promo_group(promo_group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Этот тариф недоступен для вашей группы',
            )

        period_days = payload.period_days

        # Validate period exists in tariff
        available_periods = [int(p) for p in (tariff.period_prices or {}).keys()]
        if period_days not in available_periods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Период не доступен для этого тарифа',
            )

        # Find existing subscription for this tariff (renewal pricing)
        await db.refresh(user, ['subscriptions'])
        if settings.is_multi_tariff_enabled():
            from app.database.crud.subscription import get_subscription_by_user_and_tariff
            existing_sub = await get_subscription_by_user_and_tariff(db, user.id, tariff.id)
        else:
            existing_sub = getattr(user, 'subscription', None)

        effective_device_limit = tariff.device_limit
        device_limit_for_pricing = None
        if existing_sub and existing_sub.tariff_id == tariff.id:
            device_limit_for_pricing = existing_sub.device_limit
            if (existing_sub.device_limit or 0) > (tariff.device_limit or 0):
                effective_device_limit = existing_sub.device_limit

        # Calculate price with tariff-specific engine
        result = await pricing_engine.calculate_tariff_purchase_price(
            tariff,
            period_days,
            device_limit=device_limit_for_pricing,
            user=user,
        )
        price_kopeks = result.final_total

        if price_kopeks <= 0 and result.original_total <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Некорректная конфигурация цены тарифа',
            )

        balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)

        # ── Sufficient balance — activate immediately ─────────────────────────
        if payload.use_balance and balance_covers_price(balance_kopeks, price_kopeks):
            from app.database.crud.subscription import (
                create_paid_subscription,
                extend_subscription,
                restore_reserve_grace_if_active,
            )
            from app.database.crud.transaction import create_transaction
            from app.database.crud.user import subtract_user_balance
            from app.database.models import PaymentMethod, TransactionType
            from app.services.subscription_service import SubscriptionService

            description = f"Покупка тарифа '{tariff.name}' на {period_days} дней"
            bd = result.breakdown
            group_pcts = bd.get('group_discount_pct', {})
            discount_pct = group_pcts.get('period', 0)
            if discount_pct > 0:
                description += f' (скидка {discount_pct}%)'

            ok = await subtract_user_balance(db, user, price_kopeks, description)
            if not ok:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail='Недостаточно средств на балансе',
                )

            # Resolve server squads from tariff
            squads = tariff.allowed_squads or []
            if not squads:
                from app.database.crud.server_squad import get_all_server_squads
                all_servers, _ = await get_all_server_squads(db, available_only=True)
                squads = [s.squad_uuid for s in all_servers if s.squad_uuid]

            traffic_limit_gb = tariff.traffic_limit_gb

            restore_reserve_squads = False
            if existing_sub and existing_sub.tariff_id == tariff.id:
                restore_reserve_squads = restore_reserve_grace_if_active(existing_sub)
                subscription = await extend_subscription(
                    db=db,
                    subscription=existing_sub,
                    days=period_days,
                    tariff_id=tariff.id,
                    traffic_limit_gb=traffic_limit_gb,
                    device_limit=effective_device_limit,
                    connected_squads=squads,
                )
            else:
                subscription = await create_paid_subscription(
                    db=db,
                    user=user,
                    days=period_days,
                    traffic_limit_gb=traffic_limit_gb,
                    device_limit=effective_device_limit,
                    connected_squads=squads,
                    tariff_id=tariff.id,
                    payment_method=PaymentMethod.BALANCE,
                )

            if price_kopeks > 0:
                await create_transaction(
                    db=db,
                    user_id=user.id,
                    type=TransactionType.SUBSCRIPTION_PAYMENT,
                    amount_kopeks=price_kopeks,
                    description=description,
                )

            try:
                await SubscriptionService().update_remnawave_user(
                    db, subscription, sync_squads=restore_reserve_squads
                )
            except Exception as sync_err:
                logger.warning('mobile buy-tariff: remnawave sync failed', error=sync_err)

            # Admin notification
            _purchase_type = 'renewal' if (existing_sub and existing_sub.tariff_id == tariff.id) else 'first_purchase'
            await _notify_mobile_purchase(
                db, user, subscription,
                period_days=period_days,
                amount_kopeks=price_kopeks,
                purchase_type=_purchase_type,
            )

            return BuyResponse(
                status='success',
                message=f"Тариф '{tariff.name}' активирован",
                subscription=_serialize_subscription(subscription),
            )

        # ── Insufficient balance — create YooKassa payment ────────────────────
        if not settings.is_yookassa_enabled():
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail='Недостаточно средств. Пополните баланс в боте.',
            )

        from app.services.payment_service import PaymentService
        from app.services.user_cart_service import user_cart_service

        cart_data = {
            'cart_mode': 'tariff_purchase',
            'tariff_id': tariff.id,
            'period_days': period_days,
            'total_price': price_kopeks,
            'user_id': user.id,
            'traffic_limit_gb': tariff.traffic_limit_gb,
            'device_limit': effective_device_limit,
            'allowed_squads': tariff.allowed_squads or [],
            'source': 'mobile',
        }
        try:
            await user_cart_service.save_user_cart(user.id, cart_data)
        except Exception as cart_err:
            logger.warning('mobile buy-tariff: failed to save cart', error=cart_err)

        payment_result = await PaymentService().create_yookassa_payment(
            db=db,
            user_id=user.id,
            amount_kopeks=price_kopeks,
            description=f"Тариф '{tariff.name}' на {period_days} дней",
            metadata={
                'type': 'mobile_tariff_purchase',
                'tariff_id': tariff.id,
                'period_days': period_days,
            },
        )

        if not payment_result or not payment_result.get('confirmation_url'):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Не удалось создать платёж',
            )

        return BuyResponse(
            status='payment_required',
            message='Пополните баланс для активации тарифа',
            payment_url=payment_result['confirmation_url'],
            amount_kopeks=price_kopeks,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error in buy-tariff', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при покупке тарифа',
        ) from exc


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
    user: User = Depends(get_current_cabinet_user),
) -> BalanceResponse:
    """Return the current account balance for the authenticated user."""
    balance_kopeks = int(getattr(user, 'balance_kopeks', 0) or 0)
    currency = (getattr(user, 'balance_currency', None) or 'RUB').upper()

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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> BalanceTopupResponse:
    """
    Create a YooKassa payment to top up the user's account balance.

    Returns a confirmation URL that the app should open in an external browser.
    After a successful payment, the backend webhook will credit the balance.
    """
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
                'telegram_id': str(user.telegram_id),
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
        logger.error('Error creating balance topup payment', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при создании платежа',
        ) from exc


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
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> AutopayResponse:
    """Enable or disable automatic subscription renewal from account balance."""
    try:
        await db.refresh(user, ['subscriptions'])
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
        logger.error('Error updating autopay', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обновлении настроек автопродления',
        ) from exc

    return AutopayResponse(autopay_enabled=enabled, message=message)


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/tariff/switch/preview
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/tariff/switch/preview',
    response_model=TariffSwitchPreviewResponse,
    summary='Предпросмотр стоимости смены тарифа',
    tags=['mobile'],
)
async def preview_tariff_switch_mobile(
    payload: TariffSwitchRequest,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> TariffSwitchPreviewResponse:
    """Calculate the cost of switching to a different tariff without committing."""
    from datetime import UTC, datetime

    try:
        if not settings.is_tariffs_mode():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Tariffs mode is not enabled',
            )

        await db.refresh(user, ['subscriptions'])
        subscription = getattr(user, 'subscription', None)

        if not subscription or not subscription.tariff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Нет активной подписки с тарифом',
            )

        actual_status = subscription.actual_status
        if actual_status == 'expired':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'code': 'subscription_expired',
                    'message': 'Подписка истекла. Оформите новый тариф.',
                    'use_purchase_flow': True,
                },
            )
        if actual_status not in ('active', 'trial'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'code': 'subscription_not_active',
                    'message': f'Подписка неактивна (статус: {actual_status}). Смена тарифа невозможна.',
                },
            )

        if subscription.tariff_id == payload.tariff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Вы уже на этом тарифе',
            )

        current_tariff = await get_tariff_by_id(db, subscription.tariff_id)
        new_tariff = await get_tariff_by_id(db, payload.tariff_id)

        if not new_tariff or not new_tariff.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Тариф не найден или неактивен',
            )

        # Check tariff availability for user's promo group
        promo_group = user.get_primary_promo_group() if hasattr(user, 'get_primary_promo_group') else None
        if promo_group is None:
            promo_group = getattr(user, 'promo_group', None)
        promo_group_id = promo_group.id if promo_group else None
        if not new_tariff.is_available_for_promo_group(promo_group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Тариф недоступен для вашей группы',
            )

        # Calculate remaining days
        remaining_days = 0
        if subscription.end_date and subscription.end_date > datetime.now(UTC):
            delta = subscription.end_date - datetime.now(UTC)
            remaining_days = max(0, delta.days)

        switch_result = pricing_engine.calculate_tariff_switch_cost(
            current_tariff,
            new_tariff,
            remaining_days,
            user=user,
        )
        upgrade_cost = switch_result.upgrade_cost
        is_upgrade = switch_result.is_upgrade
        base_upgrade_cost = switch_result.raw_cost
        discount_value = switch_result.discount_value
        period_discount_percent = switch_result.effective_discount_pct

        # Extra devices surcharge (Family tariff only)
        base_switch_cost = switch_result.upgrade_cost  # tariff-only part, before device add-on
        extra_device_cost = 0
        devices_requested: int | None = None
        if payload.devices and payload.devices > new_tariff.device_limit and remaining_days > 0:
            dev_price_kop = getattr(new_tariff, 'device_price_kopeks', None) or 0
            if dev_price_kop > 0:
                extra_devices = max(0, payload.devices - new_tariff.device_limit)
                # Prorated per-day cost: device_price_kopeks / 30 days × extra × remaining
                extra_device_cost = extra_devices * dev_price_kop * remaining_days // 30
                upgrade_cost += extra_device_cost
                is_upgrade = True
            devices_requested = payload.devices

        balance = user.balance_kopeks or 0
        has_enough = balance >= upgrade_cost
        missing = max(0, upgrade_cost - balance) if not has_enough else 0

        return TariffSwitchPreviewResponse(
            can_switch=has_enough,
            current_tariff_id=current_tariff.id if current_tariff else None,
            current_tariff_name=current_tariff.name if current_tariff else None,
            new_tariff_id=new_tariff.id,
            new_tariff_name=new_tariff.name,
            remaining_days=remaining_days,
            upgrade_cost_kopeks=upgrade_cost,
            upgrade_cost_label=settings.format_price(upgrade_cost) if upgrade_cost > 0 else 'Бесплатно',
            balance_kopeks=balance,
            balance_label=settings.format_price(balance),
            has_enough_balance=has_enough,
            missing_amount_kopeks=missing,
            missing_amount_label=settings.format_price(missing) if missing > 0 else '',
            is_upgrade=is_upgrade,
            discount_percent=period_discount_percent if period_discount_percent > 0 and discount_value > 0 else None,
            discount_kopeks=discount_value if period_discount_percent > 0 and discount_value > 0 else None,
            base_upgrade_cost_kopeks=base_upgrade_cost if period_discount_percent > 0 and discount_value > 0 else None,
            base_switch_cost_kopeks=base_switch_cost if extra_device_cost > 0 else None,
            extra_device_cost_kopeks=extra_device_cost if extra_device_cost > 0 else None,
            devices_requested=devices_requested,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error previewing tariff switch', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при расчёте стоимости смены тарифа',
        ) from exc


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/tariff/switch
# ---------------------------------------------------------------------------


@router.post(
    '/subscription/tariff/switch',
    response_model=TariffSwitchResponse,
    summary='Сменить тариф',
    tags=['mobile'],
)
async def switch_tariff_mobile(
    payload: TariffSwitchRequest,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> TariffSwitchResponse:
    """Switch to a different tariff. Keeps existing end_date; charges difference for upgrades."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete as sql_delete, select

    from app.database.crud.subscription import calc_device_limit_on_tariff_switch
    from app.database.crud.transaction import create_transaction, emit_transaction_side_effects
    from app.database.crud.user import lock_user_for_pricing, subtract_user_balance
    from app.database.models import PaymentMethod, Subscription, TrafficPurchase, TransactionType

    try:
        if not settings.is_tariffs_mode():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Tariffs mode is not enabled',
            )

        await db.refresh(user, ['subscriptions'])
        subscription = getattr(user, 'subscription', None)

        if not subscription or not subscription.tariff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Нет активной подписки с тарифом',
            )

        # Lock subscription row to prevent concurrent switches
        locked_result = await db.execute(
            select(Subscription)
            .where(Subscription.id == subscription.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        subscription = locked_result.scalar_one()

        actual_status = subscription.actual_status
        if actual_status == 'expired':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'code': 'subscription_expired',
                    'message': 'Подписка истекла. Оформите новый тариф.',
                    'use_purchase_flow': True,
                },
            )
        if actual_status not in ('active', 'trial'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'code': 'subscription_not_active',
                    'message': f'Подписка неактивна (статус: {actual_status}). Смена тарифа невозможна.',
                },
            )

        if subscription.tariff_id == payload.tariff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Вы уже на этом тарифе',
            )

        current_tariff = await get_tariff_by_id(db, subscription.tariff_id)
        new_tariff = await get_tariff_by_id(db, payload.tariff_id)

        if not new_tariff or not new_tariff.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Тариф не найден или неактивен',
            )

        # Check tariff availability for user's promo group
        promo_group = user.get_primary_promo_group() if hasattr(user, 'get_primary_promo_group') else None
        if promo_group is None:
            promo_group = getattr(user, 'promo_group', None)
        promo_group_id = promo_group.id if promo_group else None
        if not new_tariff.is_available_for_promo_group(promo_group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Тариф недоступен для вашей группы',
            )

        # Lock user before price computation (prevent TOCTOU on promo offer)
        user = await lock_user_for_pricing(db, user.id)

        # Calculate remaining days
        remaining_days = 0
        if subscription.end_date and subscription.end_date > datetime.now(UTC):
            delta = subscription.end_date - datetime.now(UTC)
            remaining_days = max(0, delta.days)

        switch_result = pricing_engine.calculate_tariff_switch_cost(
            current_tariff,
            new_tariff,
            remaining_days,
            user=user,
        )
        upgrade_cost = switch_result.upgrade_cost
        base_upgrade_cost = switch_result.raw_cost
        discount_value = switch_result.discount_value
        period_discount_percent = switch_result.effective_discount_pct
        new_period_days = switch_result.new_period_days

        # Extra devices surcharge (Family tariff only)
        extra_device_cost = 0
        requested_devices: int | None = None
        if payload.devices and payload.devices > new_tariff.device_limit and remaining_days > 0:
            dev_price_kop = getattr(new_tariff, 'device_price_kopeks', None) or 0
            tariff_max = getattr(new_tariff, 'max_device_limit', None)
            capped_devices = min(payload.devices, tariff_max) if tariff_max else payload.devices
            if dev_price_kop > 0 and capped_devices > new_tariff.device_limit:
                extra_devices = capped_devices - new_tariff.device_limit
                extra_device_cost = extra_devices * dev_price_kop * remaining_days // 30
                upgrade_cost += extra_device_cost
            requested_devices = capped_devices

        new_is_daily = getattr(new_tariff, 'is_daily', False)
        current_is_daily = getattr(current_tariff, 'is_daily', False) if current_tariff else False
        switching_to_daily = not current_is_daily and new_is_daily
        switching_from_daily = current_is_daily and not new_is_daily

        if switching_to_daily and (getattr(new_tariff, 'daily_price_kopeks', 0) or 0) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Суточный тариф имеет некорректную цену',
            )

        # Charge if upgrade
        switch_transaction = None
        old_tariff_name = current_tariff.name if current_tariff else 'Unknown'

        if upgrade_cost > 0:
            if not payload.use_balance or not balance_covers_price(user.balance_kopeks, upgrade_cost):
                if not settings.is_yookassa_enabled():
                    missing = max(0, upgrade_cost - user.balance_kopeks)
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={
                            'code': 'insufficient_funds',
                            'message': f'Недостаточно средств. Не хватает {settings.format_price(missing)}',
                            'missing_amount': missing,
                        },
                    )

                from app.services.payment_service import PaymentService
                from app.services.user_cart_service import user_cart_service

                payment_service = PaymentService()
                payment_result = await payment_service.create_yookassa_payment(
                    db=db,
                    user_id=user.id,
                    amount_kopeks=upgrade_cost,
                    description=f"Переход на тариф '{new_tariff.name}'",
                    metadata={'type': 'mobile_tariff_purchase'},
                )
                if not payment_result or not payment_result.get('confirmation_url'):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail='Не удалось создать платёж',
                    )

                try:
                    await user_cart_service.save_user_cart(user.id, {
                        'cart_mode': 'tariff_switch',
                        'subscription_id': subscription.id,
                        'tariff_id': new_tariff.id,
                        'devices': requested_devices,
                        'total_price': upgrade_cost,
                        'source': 'mobile',
                    })
                except Exception as cart_err:
                    logger.warning('mobile tariff switch: failed to save cart', error=cart_err)

                return TariffSwitchResponse(
                    success=False,
                    payment_required=True,
                    payment_url=payment_result['confirmation_url'],
                    message='Пополните баланс для смены тарифа',
                    old_tariff_name=old_tariff_name,
                    new_tariff_id=new_tariff.id,
                    new_tariff_name=new_tariff.name,
                    charged_kopeks=upgrade_cost,
                    balance_kopeks=user.balance_kopeks,
                    balance_label=settings.format_price(user.balance_kopeks),
                )

            if switching_to_daily:
                description = f"Переход на суточный тариф '{new_tariff.name}'"
            elif switching_from_daily:
                description = f"Переход с суточного на тариф '{new_tariff.name}' ({new_period_days} дней)"
            else:
                description = f"Переход на тариф '{new_tariff.name}' (доплата за {remaining_days} дней)"

            if extra_device_cost > 0 and requested_devices is not None:
                description += f' + {requested_devices} устр.'

            if period_discount_percent > 0 and discount_value > 0:
                description += f' (скидка {period_discount_percent}%)'

            success = await subtract_user_balance(
                db,
                user,
                upgrade_cost,
                description,
                consume_promo_offer=switch_result.offer_discount_pct > 0,
                mark_as_paid_subscription=True,
                commit=False,
            )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Не удалось списать средства',
                )

            switch_transaction = await create_transaction(
                db=db,
                user_id=user.id,
                type=TransactionType.SUBSCRIPTION_PAYMENT,
                amount_kopeks=upgrade_cost,
                description=description,
                payment_method=PaymentMethod.BALANCE,
                commit=False,
            )
        else:
            description = f"Переход на тариф '{new_tariff.name}'"
            await create_transaction(
                db=db,
                user_id=user.id,
                type=TransactionType.SUBSCRIPTION_PAYMENT,
                amount_kopeks=0,
                description=description,
                commit=False,
            )

        # Re-load subscription to avoid MissingGreenlet after subtract_user_balance
        await db.refresh(subscription)

        subscription.tariff_id = new_tariff.id
        subscription.traffic_limit_gb = new_tariff.traffic_limit_gb
        if requested_devices is not None:
            # User explicitly chose device count — use it directly (already capped to max)
            subscription.device_limit = requested_devices
        else:
            subscription.device_limit = calc_device_limit_on_tariff_switch(
                current_device_limit=subscription.device_limit,
                old_tariff_device_limit=current_tariff.device_limit if current_tariff else None,
                new_tariff_device_limit=new_tariff.device_limit,
                max_device_limit=new_tariff.max_device_limit,
            )
        subscription.connected_squads = new_tariff.allowed_squads or []

        # Reset purchased traffic
        await db.execute(sql_delete(TrafficPurchase).where(TrafficPurchase.subscription_id == subscription.id))
        subscription.purchased_traffic_gb = 0
        subscription.traffic_reset_at = None

        if settings.RESET_TRAFFIC_ON_TARIFF_SWITCH:
            subscription.traffic_used_gb = 0.0

        if switching_to_daily:
            subscription.end_date = datetime.now(UTC) + timedelta(days=1)
            subscription.last_daily_charge_at = datetime.now(UTC)
            subscription.is_daily_paused = False
        elif switching_from_daily:
            subscription.end_date = datetime.now(UTC) + timedelta(days=new_period_days)
            subscription.is_daily_paused = False

        subscription.updated_at = datetime.now(UTC)
        await db.commit()

        # Emit side-effects after atomic commit
        if upgrade_cost > 0 and switch_transaction:
            await emit_transaction_side_effects(
                db,
                switch_transaction,
                amount_kopeks=upgrade_cost,
                user_id=user.id,
                type=TransactionType.SUBSCRIPTION_PAYMENT,
                payment_method=PaymentMethod.BALANCE,
            )

        # Sync with RemnaWave
        from app.services.remnawave_service import RemnaWaveService
        from app.services.subscription_service import SubscriptionService

        should_reset_traffic = settings.RESET_TRAFFIC_ON_TARIFF_SWITCH
        await db.refresh(subscription)

        try:
            subscription_service = SubscriptionService()
            _has_panel = getattr(user, 'remnawave_uuid', None)
            if _has_panel:
                await subscription_service.update_remnawave_user(
                    db,
                    subscription,
                    reset_traffic=should_reset_traffic,
                    reset_reason='смена тарифа',
                    sync_squads=True,
                )
            else:
                await subscription_service.create_remnawave_user(
                    db,
                    subscription,
                    reset_traffic=should_reset_traffic,
                    reset_reason='смена тарифа',
                )
        except Exception as e:
            logger.error('Failed to sync tariff switch with RemnaWave', error=e)

        # Reset all devices
        devices_reset = False
        _uuid = user.remnawave_uuid
        if _uuid:
            try:
                service = RemnaWaveService()
                async with service.get_api_client() as api:
                    await api.reset_user_devices(_uuid)
                    devices_reset = True
            except Exception as e:
                logger.error('Failed to reset devices on tariff switch', error=e)

        # Admin notification
        try:
            from aiogram import Bot

            from app.services.admin_notification_service import AdminNotificationService

            if getattr(settings, 'ADMIN_NOTIFICATIONS_ENABLED', False) and settings.BOT_TOKEN:
                bot = Bot(token=settings.BOT_TOKEN)
                try:
                    notification_service = AdminNotificationService(bot)
                    await notification_service.send_subscription_purchase_notification(
                        db=db,
                        user=user,
                        subscription=subscription,
                        transaction=switch_transaction if upgrade_cost > 0 else None,
                        period_days=remaining_days if remaining_days > 0 else new_period_days,
                        was_trial_conversion=False,
                        amount_kopeks=upgrade_cost,
                        purchase_type='tariff_switch',
                        source=_MOBILE_SOURCE,
                    )
                finally:
                    await bot.session.close()
        except Exception as e:
            logger.error('Failed to send admin notification for tariff switch', error=e)

        await db.refresh(subscription)
        await db.refresh(user)

        return TariffSwitchResponse(
            success=True,
            message=f"Тариф изменён с '{old_tariff_name}' на '{new_tariff.name}'"
            + (' (устройства сброшены)' if devices_reset else ''),
            old_tariff_name=old_tariff_name,
            new_tariff_id=new_tariff.id,
            new_tariff_name=new_tariff.name,
            charged_kopeks=upgrade_cost,
            balance_kopeks=user.balance_kopeks,
            balance_label=settings.format_price(user.balance_kopeks),
            subscription=None,
            discount_percent=period_discount_percent if period_discount_percent > 0 and discount_value > 0 else None,
            discount_kopeks=discount_value if period_discount_percent > 0 and discount_value > 0 else None,
            base_charged_kopeks=base_upgrade_cost if period_discount_percent > 0 and discount_value > 0 else None,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error switching tariff', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при смене тарифа',
        ) from exc


# ---------------------------------------------------------------------------
# GET /mobile/v1/devices
# ---------------------------------------------------------------------------


@router.get(
    '/devices',
    response_model=DevicesListResponse,
    summary='Список подключённых устройств',
    tags=['mobile'],
)
async def list_devices_mobile(
    user: User = Depends(get_current_cabinet_user),
) -> DevicesListResponse:
    """Return HWID devices registered for the current user."""
    try:
        _uuid = user.remnawave_uuid
        if not _uuid:
            return DevicesListResponse(devices=[], count=0, device_limit=0)

        from app.services.remnawave_service import RemnaWaveService

        service = RemnaWaveService()
        async with service.get_api_client() as api:
            raw = await api.get_user_devices_all(_uuid)

        items = raw.get('devices') or []
        if not isinstance(items, list):
            items = []

        sub = getattr(user, 'subscription', None)
        device_limit = sub.device_limit if sub else 0

        from app.mobile.schemas.subscription import DeviceInfo
        devices = []
        for d in items:
            hwid = d.get('hwid') or d.get('deviceId') or d.get('id') or ''
            if not hwid:
                continue
            created = d.get('updatedAt') or d.get('lastSeen') or d.get('createdAt') or d.get('created_at') or None
            # RemnaWave returns platform and deviceModel as separate fields.
            platform = d.get('platform') or d.get('platformType') or None
            device_model = d.get('deviceModel') or d.get('model') or None
            # Fallback name: userAgent or legacy name field (used for UA-based parsing)
            name = d.get('userAgent') or d.get('user_agent') or d.get('name') or None
            devices.append(DeviceInfo(
                hwid=hwid,
                name=name,
                platform=platform,
                device_model=device_model,
                created_at=created,
            ))

        return DevicesListResponse(devices=devices, count=len(devices), device_limit=device_limit)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error listing devices', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при получении списка устройств',
        ) from exc


# ---------------------------------------------------------------------------
# DELETE /mobile/v1/devices
# ---------------------------------------------------------------------------


@router.delete(
    '/devices',
    response_model=DevicesResetResponse,
    summary='Сбросить все подключённые устройства',
    tags=['mobile'],
)
async def reset_devices_mobile(
    user: User = Depends(get_current_cabinet_user),
) -> DevicesResetResponse:
    """Reset (delete) all HWID devices for the current user."""
    try:
        _uuid = user.remnawave_uuid
        if not _uuid:
            return DevicesResetResponse(success=True, message='Устройств нет')

        from app.services.remnawave_service import RemnaWaveService

        service = RemnaWaveService()
        async with service.get_api_client() as api:
            await api.reset_user_devices(_uuid)

        return DevicesResetResponse(success=True, message='Все устройства сброшены')

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error resetting devices', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при сбросе устройств',
        ) from exc


# ---------------------------------------------------------------------------
# POST /mobile/v1/devices/delete  — удалить одно устройство
# ---------------------------------------------------------------------------


@router.post(
    '/devices/delete',
    response_model=DevicesResetResponse,
    summary='Удалить одно подключённое устройство',
    tags=['mobile'],
)
async def delete_device_mobile(
    payload: DeviceDeleteRequest,
    user: User = Depends(get_current_cabinet_user),
) -> DevicesResetResponse:
    """Remove a single HWID device by its fingerprint."""
    try:
        _uuid = user.remnawave_uuid
        if not _uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Пользователь не синхронизирован с панелью',
            )

        from app.services.remnawave_service import RemnaWaveService

        service = RemnaWaveService()
        async with service.get_api_client() as api:
            ok = await api.remove_device(_uuid, payload.hwid)

        if ok:
            return DevicesResetResponse(success=True, message='Устройство удалено')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не удалось удалить устройство',
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Error deleting device', user_id=user.id, error=exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при удалении устройства',
        ) from exc
