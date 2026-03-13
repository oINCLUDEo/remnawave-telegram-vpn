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
    calc_subscription_price,
    get_balance,
    get_subscription_options,
    set_autopay,
    topup_balance,
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
