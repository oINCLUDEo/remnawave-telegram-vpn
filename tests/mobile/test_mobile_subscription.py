"""Tests for the mobile subscription endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.mobile.routes.subscription import (
    buy_subscription,
    calc_subscription_price,
    calc_upgrade_price,
    get_balance,
    get_subscription_options,
    set_autopay,
    topup_balance,
    upgrade_subscription,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, status='active', balance_kopeks=5000, subscription=None):
    user = MagicMock()
    user.status = status
    user.telegram_id = 123456789
    user.id = 42
    user.first_name = 'Ivan'
    user.last_name = 'Petrov'
    user.balance_kopeks = balance_kopeks
    user.balance_currency = 'RUB'
    user.subscription = subscription
    user.language = 'ru'
    user.promo_group_id = None
    return user


def _make_subscription(*, sub_status='active', is_trial=False):
    sub = MagicMock()
    sub.status = sub_status
    sub.is_trial = is_trial
    sub.traffic_limit_gb = 100
    sub.traffic_used_gb = 10.0
    sub.purchased_traffic_gb = 0
    sub.device_limit = 2
    sub.autopay_enabled = False
    sub.connected_squads = ['uuid-1']
    sub.subscription_url = 'https://example.com/sub/abc'
    from datetime import UTC, datetime

    sub.end_date = datetime(2099, 1, 1, tzinfo=UTC)
    return sub


def _db_patch(user):
    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda u, attrs=None: None)
    mock_db.close = AsyncMock()
    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()
    return mock_db, mock_session_class, mock_engine


# ---------------------------------------------------------------------------
# GET /mobile/v1/balance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_balance_returns_balance():
    user = _make_user(balance_kopeks=12500)
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await get_balance(x_telegram_id=123456789)

    assert result.balance_kopeks == 12500
    assert result.balance_rub == 125.0
    assert result.currency == 'RUB'


@pytest.mark.asyncio
async def test_get_balance_unknown_user_raises_404():
    from fastapi import HTTPException

    mock_db, mock_session_class, mock_engine = _db_patch(None)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=None),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        with pytest.raises(HTTPException) as exc_info:
            await get_balance(x_telegram_id=9999)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# PUT /mobile/v1/subscription/autopay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_autopay_enables_autopay():
    sub = _make_subscription()
    user = _make_user(subscription=sub)
    mock_db, mock_session_class, mock_engine = _db_patch(user)
    mock_db.commit = AsyncMock()

    from app.mobile.schemas.subscription import AutopayRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await set_autopay(
            payload=AutopayRequest(enabled=True),
            x_telegram_id=123456789,
        )

    assert result.autopay_enabled is True


@pytest.mark.asyncio
async def test_set_autopay_no_subscription_raises_404():
    from fastapi import HTTPException

    user = _make_user(subscription=None)
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    from app.mobile.schemas.subscription import AutopayRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        with pytest.raises(HTTPException) as exc_info:
            await set_autopay(
                payload=AutopayRequest(enabled=True),
                x_telegram_id=123456789,
            )

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /mobile/v1/subscription/options
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_subscription_options_returns_context():
    user = _make_user()
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    # Build a minimal mock context
    mock_period = MagicMock()
    mock_period.to_payload.return_value = {'id': 'days:30', 'label': '1 месяц'}
    mock_context = MagicMock()
    mock_context.periods = [mock_period]
    mock_context.balance_kopeks = 5000
    mock_context.currency = 'RUB'

    mock_service = MagicMock()
    mock_service.build_options = AsyncMock(return_value=mock_context)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
        patch(
            'app.services.subscription_purchase_service.MiniAppSubscriptionPurchaseService',
            return_value=mock_service,
        ),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await get_subscription_options(x_telegram_id=123456789)

    assert result.has_subscription is False
    assert 'periods' in result.context
    assert result.context['balance_kopeks'] == 5000


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/calc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calc_subscription_price_returns_total():
    user = _make_user()
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    mock_period = MagicMock()
    mock_period.to_payload.return_value = {'id': 'days:30', 'label': '1 месяц'}
    mock_context = MagicMock()
    mock_context.periods = [mock_period]
    mock_context.balance_kopeks = 5000
    mock_context.currency = 'RUB'

    mock_pricing = MagicMock()
    mock_pricing.final_total = 39900
    mock_pricing.details = {}

    mock_service = MagicMock()
    mock_service.build_options = AsyncMock(return_value=mock_context)
    mock_service.parse_selection = MagicMock(return_value=MagicMock())
    mock_service.calculate_pricing = AsyncMock(return_value=mock_pricing)
    mock_service.build_preview_payload = MagicMock(return_value={'total': '399 ₽'})

    from app.mobile.schemas.subscription import SubscriptionSelectionRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
        patch(
            'app.services.subscription_purchase_service.MiniAppSubscriptionPurchaseService',
            return_value=mock_service,
        ),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await calc_subscription_price(
            payload=SubscriptionSelectionRequest(period_id='days:30', traffic_value=50, devices=2),
            x_telegram_id=123456789,
        )

    assert result.total_kopeks == 39900
    assert result.total_rub == 399.0


# ---------------------------------------------------------------------------
# POST /mobile/v1/balance/topup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_topup_balance_when_yookassa_disabled_raises_402():
    from fastapi import HTTPException

    user = _make_user(balance_kopeks=0)
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    from app.mobile.schemas.subscription import BalanceTopupRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_settings.is_yookassa_enabled.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await topup_balance(
                payload=BalanceTopupRequest(amount_kopeks=30000),
                x_telegram_id=123456789,
            )

    assert exc_info.value.status_code == 402


@pytest.mark.asyncio
async def test_topup_balance_creates_payment_url():
    user = _make_user(balance_kopeks=0)
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    from app.mobile.schemas.subscription import BalanceTopupRequest

    mock_ps_instance = MagicMock()
    mock_ps_instance.create_yookassa_payment = AsyncMock(
        return_value={'confirmation_url': 'https://yookassa.ru/pay/test'}
    )
    mock_ps_class = MagicMock(return_value=mock_ps_instance)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
        patch.dict('sys.modules', {'app.services.payment_service': MagicMock(PaymentService=mock_ps_class)}),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_settings.is_yookassa_enabled.return_value = True

        result = await topup_balance(
            payload=BalanceTopupRequest(amount_kopeks=30000),
            x_telegram_id=123456789,
        )

    assert result.status == 'payment_required'
    assert result.payment_url == 'https://yookassa.ru/pay/test'
    assert result.amount_kopeks == 30000


# ---------------------------------------------------------------------------
# _metadata_is_balance – mobile payment types must be included
# ---------------------------------------------------------------------------


def test_metadata_is_balance_recognises_standard_topup():
    from app.services.payment_verification_service import _metadata_is_balance

    payment = MagicMock()
    payment.metadata_json = {'type': 'balance_topup'}
    assert _metadata_is_balance(payment) is True


def test_metadata_is_balance_recognises_mobile_balance_topup():
    from app.services.payment_verification_service import _metadata_is_balance

    payment = MagicMock()
    payment.metadata_json = {'type': 'mobile_balance_topup'}
    assert _metadata_is_balance(payment) is True


def test_metadata_is_balance_recognises_mobile_subscription_topup():
    from app.services.payment_verification_service import _metadata_is_balance

    payment = MagicMock()
    payment.metadata_json = {'type': 'mobile_subscription_topup'}
    assert _metadata_is_balance(payment) is True


def test_metadata_is_balance_recognises_mobile_subscription_upgrade_topup():
    from app.services.payment_verification_service import _metadata_is_balance

    payment = MagicMock()
    payment.metadata_json = {'type': 'mobile_subscription_upgrade_topup'}
    assert _metadata_is_balance(payment) is True


def test_metadata_is_balance_rejects_unknown_type():
    from app.services.payment_verification_service import _metadata_is_balance

    payment = MagicMock()
    payment.metadata_json = {'type': 'simple_subscription_purchase'}
    assert _metadata_is_balance(payment) is False


def test_metadata_is_balance_empty_metadata():
    from app.services.payment_verification_service import _metadata_is_balance

    payment = MagicMock()
    payment.metadata_json = {}
    assert _metadata_is_balance(payment) is False


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/buy – cart saved on insufficient balance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_subscription_saves_cart_on_insufficient_balance():
    """When balance is insufficient, a cart must be saved in Redis."""
    user = _make_user(balance_kopeks=0)
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    # Mock the purchase service
    mock_period = MagicMock()
    mock_period.days = 30
    mock_period.id = 'days:30'
    mock_selection = MagicMock()
    mock_selection.period = mock_period
    mock_selection.traffic_value = 100
    mock_selection.devices = 2
    mock_selection.servers = ['uuid-1']
    mock_pricing = MagicMock()
    mock_pricing.final_total = 50000

    mock_service = MagicMock()
    mock_service.build_options = AsyncMock(return_value=MagicMock())
    mock_service.parse_selection = MagicMock(return_value=mock_selection)
    mock_service.calculate_pricing = AsyncMock(return_value=mock_pricing)
    mock_service_class = MagicMock(return_value=mock_service)

    mock_ps_instance = MagicMock()
    mock_ps_instance.create_yookassa_payment = AsyncMock(
        return_value={
            'confirmation_url': 'https://yookassa.ru/pay/test',
            'local_payment_id': 1,
        }
    )
    mock_ps_class = MagicMock(return_value=mock_ps_instance)

    mock_cart_service = MagicMock()
    mock_cart_service.save_user_cart = AsyncMock(return_value=True)

    from app.mobile.schemas.subscription import SubscriptionBuyRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
        patch.dict(
            'sys.modules',
            {
                'app.services.payment_service': MagicMock(PaymentService=mock_ps_class),
                'app.services.subscription_purchase_service': MagicMock(
                    MiniAppSubscriptionPurchaseService=mock_service_class,
                    PurchaseBalanceError=Exception,
                    PurchaseValidationError=Exception,
                ),
                'app.services.user_cart_service': MagicMock(user_cart_service=mock_cart_service),
            },
        ),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_settings.is_yookassa_enabled.return_value = True

        result = await buy_subscription(
            payload=SubscriptionBuyRequest(period_id='days:30'),
            x_telegram_id=123456789,
        )

    assert result.status == 'payment_required'
    mock_cart_service.save_user_cart.assert_called_once()
    call_args = mock_cart_service.save_user_cart.call_args
    saved_cart = call_args[0][1] if call_args[0] else call_args[1].get('cart_data') or list(call_args[1].values())[0]
    assert saved_cart.get('period_days') == 30
    assert saved_cart.get('source') == 'mobile'


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/upgrade/calc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calc_upgrade_price_returns_amount():
    """upgrade/calc returns amount_kopeks without applying any changes."""
    user = _make_user()
    sub = _make_subscription()
    user.subscription = sub
    mock_db, mock_session_class, mock_engine = _db_patch(user)

    mock_period = MagicMock()
    mock_period.id = 'days:30'
    mock_period.days = 30
    mock_context = MagicMock()
    mock_context.periods = [mock_period]

    mock_pricing = MagicMock()
    mock_pricing.final_total = 8000

    mock_service = MagicMock()
    mock_service.build_options = AsyncMock(return_value=mock_context)
    mock_service.parse_selection = MagicMock(return_value=MagicMock())
    mock_service.calculate_pricing = AsyncMock(return_value=mock_pricing)

    from app.mobile.schemas.subscription import SubscriptionUpgradeRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
        patch(
            'app.services.subscription_purchase_service.MiniAppSubscriptionPurchaseService',
            return_value=mock_service,
        ),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await calc_upgrade_price(
            payload=SubscriptionUpgradeRequest(traffic_add=50),
            x_telegram_id=123456789,
        )

    assert result.amount_kopeks == 8000
    assert result.amount_rub == 80.0


# ---------------------------------------------------------------------------
# POST /mobile/v1/subscription/upgrade — traffic-only (no period extension)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upgrade_subscription_traffic_only_does_not_extend_period():
    """Traffic-only upgrade must NOT extend the subscription end_date."""
    from datetime import UTC, datetime

    user = _make_user(balance_kopeks=50000)
    sub = _make_subscription()
    original_end_date = sub.end_date
    user.subscription = sub
    mock_db, mock_session_class, mock_engine = _db_patch(user)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj, attrs=None: None)

    mock_period = MagicMock()
    mock_period.id = 'days:30'
    mock_period.days = 30
    mock_context = MagicMock()
    mock_context.periods = [mock_period]

    mock_pricing = MagicMock()
    mock_pricing.final_total = 5000
    mock_pricing.promo_discount_value = 0

    mock_service = MagicMock()
    mock_service.build_options = AsyncMock(return_value=mock_context)
    mock_service.parse_selection = MagicMock(return_value=MagicMock())
    mock_service.calculate_pricing = AsyncMock(return_value=mock_pricing)

    from app.mobile.schemas.subscription import SubscriptionUpgradeRequest

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
        patch(
            'app.services.subscription_purchase_service.MiniAppSubscriptionPurchaseService',
            return_value=mock_service,
        ),
        patch(
            'app.database.crud.user.subtract_user_balance',
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await upgrade_subscription(
            payload=SubscriptionUpgradeRequest(traffic_add=50),
            x_telegram_id=123456789,
        )

    assert result.status == 'success'
    # end_date must not have been modified
    assert sub.end_date == original_end_date
    # traffic_limit_gb must have been incremented
    assert sub.traffic_limit_gb == 150
    # submit_purchase (which extends period) must NOT have been called
    mock_service.submit_purchase.assert_not_called()
