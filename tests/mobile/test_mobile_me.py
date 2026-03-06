"""Tests for the mobile GET /me endpoint."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.mobile.routes.me import get_me
from app.mobile.schemas.me import MeMobileResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, status='active', subscription=None):
    user = MagicMock()
    user.status = status
    user.telegram_id = 123456789
    user.first_name = 'Ivan'
    user.last_name = 'Petrov'
    user.username = 'ivanp'
    user.subscription = subscription
    return user


def _make_subscription(*, sub_status='active', is_trial=False, end_ts=9999999999):
    sub = MagicMock()
    sub.status = sub_status
    sub.is_trial = is_trial
    sub.end_date = datetime.fromtimestamp(end_ts, tz=UTC)
    sub.traffic_limit_gb = 100
    sub.traffic_used_gb = 23.5
    sub.purchased_traffic_gb = 0
    sub.subscription_url = 'https://example.com/sub/abc'
    sub.device_limit = 3
    return sub


def _db_ctx(user):
    """Return a mock async DB context that yields the mock session."""
    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda u, attrs: None)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()
    return mock_db, mock_session_class, mock_engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_me_returns_404_for_unknown_user():
    from fastapi import HTTPException

    mock_db, mock_session_class, mock_engine = _db_ctx(None)

    with (
        patch('app.mobile.routes.me.settings') as mock_settings,
        patch('app.mobile.routes.me.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.me.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.me.get_user_by_telegram_id', new_callable=AsyncMock, return_value=None),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'

        with pytest.raises(HTTPException) as exc_info:
            await get_me(x_telegram_id=9999999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_me_returns_403_for_blocked_user():
    from fastapi import HTTPException

    user = _make_user(status='banned')
    mock_db, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.me.settings') as mock_settings,
        patch('app.mobile.routes.me.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.me.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.me.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'

        with pytest.raises(HTTPException) as exc_info:
            await get_me(x_telegram_id=123456789)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_me_returns_user_without_subscription():
    user = _make_user(subscription=None)
    mock_db, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.me.settings') as mock_settings,
        patch('app.mobile.routes.me.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.me.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.me.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'

        result = await get_me(x_telegram_id=123456789)

    assert isinstance(result, MeMobileResponse)
    assert result.telegram_id == 123456789
    assert result.first_name == 'Ivan'
    assert result.has_subscription is False
    assert result.subscription is None


@pytest.mark.asyncio
async def test_get_me_returns_subscription_data():
    sub = _make_subscription()
    user = _make_user(subscription=sub)
    mock_db, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.me.settings') as mock_settings,
        patch('app.mobile.routes.me.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.me.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.me.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'

        result = await get_me(x_telegram_id=123456789)

    assert isinstance(result, MeMobileResponse)
    assert result.has_subscription is True
    assert result.subscription is not None
    assert result.subscription['status'] == 'active'
    assert result.subscription['traffic_limit_gb'] == 100
    assert result.subscription['subscription_url'] == 'https://example.com/sub/abc'
    assert result.subscription['device_limit'] == 3


@pytest.mark.asyncio
async def test_get_me_subscription_includes_purchased_traffic():
    sub = _make_subscription()
    sub.traffic_limit_gb = 50
    sub.purchased_traffic_gb = 20
    user = _make_user(subscription=sub)
    mock_db, mock_session_class, mock_engine = _db_ctx(user)

    with (
        patch('app.mobile.routes.me.settings') as mock_settings,
        patch('app.mobile.routes.me.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.me.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.me.get_user_by_telegram_id', new_callable=AsyncMock, return_value=user),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'

        result = await get_me(x_telegram_id=123456789)

    # traffic_limit_gb should combine base + purchased
    assert result.subscription['traffic_limit_gb'] == 70
