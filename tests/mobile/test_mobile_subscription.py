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
    calc_subscription,
    get_balance,
    set_autopay,
)
from app.mobile.schemas.subscription import (
    AutopayRequest,
    BalanceResponse,
    SubCalcRequest,
    SubCalcResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, status='active', balance_kopeks=5000, subscription=None):
    user = MagicMock()
    user.status = status
    user.telegram_id = 111222333
    user.balance_kopeks = balance_kopeks
    user.subscription = subscription
    return user


def _make_subscription(*, autopay=False, autopay_days=3, traffic_limit_gb=50, device_limit=2):
    sub = MagicMock()
    sub.autopay_enabled = autopay
    sub.autopay_days_before = autopay_days
    sub.traffic_limit_gb = traffic_limit_gb
    sub.device_limit = device_limit
    return sub


def _db_ctx(user):
    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda u, attrs: None)
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()
    return mock_db, mock_session_class, mock_engine


# ---------------------------------------------------------------------------
# /subscription/calc tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calc_returns_price_for_known_period():
    with patch('app.mobile.routes.subscription.PERIOD_PRICES', {30: 9900, 60: 18900}):
        with patch('app.mobile.routes.subscription.settings') as mock_settings:
            mock_settings.get_traffic_price.return_value = 1100
            result = await calc_subscription(
                body=SubCalcRequest(days=30, traffic_gb=10, devices=1),
                x_telegram_id=123,
            )

    assert isinstance(result, SubCalcResponse)
    assert result.price_kopeks == 9900 + 1100
    assert result.price_rub == round(result.price_kopeks / 100, 2)


@pytest.mark.asyncio
async def test_calc_adds_device_surcharge():
    with patch('app.mobile.routes.subscription.PERIOD_PRICES', {30: 10000}):
        with patch('app.mobile.routes.subscription.settings') as mock_settings:
            mock_settings.get_traffic_price.return_value = 0
            result = await calc_subscription(
                body=SubCalcRequest(days=30, traffic_gb=0, devices=3),
                x_telegram_id=123,
            )

    # 2 extra devices × 30% of 10000 = 6000 extra
    assert result.price_kopeks == 10000 + 2 * 3000


@pytest.mark.asyncio
async def test_calc_interpolates_unknown_period():
    with patch('app.mobile.routes.subscription.PERIOD_PRICES', {30: 9900}):
        with patch('app.mobile.routes.subscription.settings') as mock_settings:
            mock_settings.get_traffic_price.return_value = 0
            result = await calc_subscription(
                body=SubCalcRequest(days=15, traffic_gb=0, devices=1),
                x_telegram_id=123,
            )

    # Should interpolate: 9900 * 15 / 30 = 4950
    assert result.price_kopeks == 4950


# ---------------------------------------------------------------------------
# /balance tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_balance_returns_user_balance():
    sub = _make_subscription(autopay=True)
    user = _make_user(balance_kopeks=35000, subscription=sub)
    _, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await get_balance(x_telegram_id=111222333)

    assert isinstance(result, BalanceResponse)
    assert result.balance_kopeks == 35000
    assert result.balance_rub == 350.0
    assert result.autopay_enabled is True


@pytest.mark.asyncio
async def test_get_balance_returns_404_for_unknown_user():
    from fastapi import HTTPException

    _, mock_session_class, mock_engine = _db_ctx(None)

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
# /subscription/autopay tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_autopay_enables():
    sub = _make_subscription(autopay=False)
    user = _make_user(subscription=sub)
    mock_db, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        result = await set_autopay(
            body=AutopayRequest(enabled=True),
            x_telegram_id=111222333,
        )

    assert result.enabled is True
    assert sub.autopay_enabled is True


@pytest.mark.asyncio
async def test_set_autopay_returns_404_when_no_subscription():
    from fastapi import HTTPException

    user = _make_user(subscription=None)
    _, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.subscription.settings') as mock_settings,
        patch('app.mobile.routes.subscription.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.subscription.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.subscription.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        with pytest.raises(HTTPException) as exc_info:
            await set_autopay(
                body=AutopayRequest(enabled=True),
                x_telegram_id=111222333,
            )

    assert exc_info.value.status_code == 404
