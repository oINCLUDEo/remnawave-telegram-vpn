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
    user.id = 1
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
    sub.reserve_access_granted_at = None
    return sub


def _mock_db():
    """Return a mock AsyncSession — get_me only ever calls db.refresh() on it."""
    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj, attrs=None: None)
    return mock_db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
# Note: user lookup and the "account not found / not authenticated" cases now
# live entirely in get_current_cabinet_user (Bearer JWT dependency) — get_me
# itself only ever receives an already-resolved User, so there's no 404 case
# to test here anymore. The "blocked account" 403 check IS still get_me's own
# (defense in depth on top of the dependency's identical check).


@pytest.mark.asyncio
async def test_get_me_returns_403_for_blocked_user():
    from fastapi import HTTPException

    user = _make_user(status='banned')

    with pytest.raises(HTTPException) as exc_info:
        await get_me(user=user, db=_mock_db())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_me_returns_user_without_subscription():
    user = _make_user(subscription=None)

    result = await get_me(user=user, db=_mock_db())

    assert isinstance(result, MeMobileResponse)
    assert result.telegram_id == 123456789
    assert result.first_name == 'Ivan'
    assert result.has_subscription is False
    assert result.subscription is None


@pytest.mark.asyncio
async def test_get_me_returns_subscription_data():
    sub = _make_subscription()
    user = _make_user(subscription=sub)

    with patch('app.mobile.routes.me.settings') as mock_settings:
        mock_settings.RESERVE_GRACE_TRAFFIC_GB = 3
        result = await get_me(user=user, db=_mock_db())

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

    with patch('app.mobile.routes.me.settings') as mock_settings:
        mock_settings.RESERVE_GRACE_TRAFFIC_GB = 3
        result = await get_me(user=user, db=_mock_db())

    # traffic_limit_gb should combine base + purchased
    assert result.subscription['traffic_limit_gb'] == 70


@pytest.mark.asyncio
async def test_get_me_reports_reserve_grace_distinctly():
    """A subscription currently in reserve-squad grace must not look like a
    normal active subscription to the client: status stays 'active' for
    backend bookkeeping, but is_reserve_grace must be true and the reported
    traffic limit must be the small grace cap, not the underlying tariff's."""
    sub = _make_subscription()
    sub.reserve_access_granted_at = datetime.now(UTC)
    user = _make_user(subscription=sub)

    with patch('app.mobile.routes.me.settings') as mock_settings:
        mock_settings.RESERVE_GRACE_TRAFFIC_GB = 3
        result = await get_me(user=user, db=_mock_db())

    assert result.subscription['is_reserve_grace'] is True
    assert result.subscription['traffic_limit_gb'] == 3
