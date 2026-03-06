"""Tests for the mobile API auth endpoints (deep-link flow)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.mobile.routes.auth import MOBILE_AUTH_START_PREFIX, auth_check, auth_init
from app.mobile.schemas.auth import MobileAuthCheckResponse, MobileAuthInitResponse


# ---------------------------------------------------------------------------
# auth_init endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_init_returns_503_when_bot_not_configured():
    from fastapi import HTTPException

    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_auth_token', return_value='abc123'),
    ):
        mock_settings.get_bot_username.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await auth_init()

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_auth_init_returns_deep_link():
    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_auth_token', return_value='abc123deadbeef'),
    ):
        mock_settings.get_bot_username.return_value = 'MyTestBot'

        result = await auth_init()

    assert isinstance(result, MobileAuthInitResponse)
    assert result.token == 'abc123deadbeef'
    assert 'MyTestBot' in result.deep_link
    assert MOBILE_AUTH_START_PREFIX in result.deep_link
    assert 'abc123deadbeef' in result.deep_link
    assert result.expires_in > 0


@pytest.mark.asyncio
async def test_auth_init_deep_link_uses_tg_scheme():
    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_auth_token', return_value='mytoken'),
    ):
        mock_settings.get_bot_username.return_value = 'SomeBot'

        result = await auth_init()

    assert result.deep_link.startswith('tg://')


@pytest.mark.asyncio
async def test_auth_init_returns_503_on_redis_error():
    from fastapi import HTTPException

    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_auth_token', side_effect=RuntimeError('Redis down')),
    ):
        mock_settings.get_bot_username.return_value = 'SomeBot'

        with pytest.raises(HTTPException) as exc_info:
            await auth_init()

    assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# auth_check endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_check_returns_expired_for_missing_token():
    with patch('app.mobile.routes.auth.get_auth_token', return_value=None):
        result = await auth_check(token='a' * 32)

    assert result.status == 'expired'
    assert result.auth is None


@pytest.mark.asyncio
async def test_auth_check_returns_pending_while_waiting():
    with patch('app.mobile.routes.auth.get_auth_token', return_value={'status': 'pending'}):
        result = await auth_check(token='a' * 32)

    assert result.status == 'pending'
    assert result.auth is None


@pytest.mark.asyncio
async def test_auth_check_returns_verified_with_auth_data():
    token_data = {
        'status': 'verified',
        'telegram_id': 123456,
        'first_name': 'Ivan',
        'last_name': 'Petrov',
        'username': 'ivanp',
    }

    mock_subscription = MagicMock()
    mock_subscription.subscription_url = 'https://example.com/sub/xyz'

    mock_user = MagicMock()
    mock_user.status = 'active'
    mock_user.subscription = mock_subscription

    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda u, attrs: None)
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with (
        patch('app.mobile.routes.auth.get_auth_token', return_value=token_data),
        patch('app.mobile.routes.auth.delete_auth_token', new_callable=AsyncMock),
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.auth.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.auth._resolve_user_data') as mock_resolve,
    ):
        mock_settings.get_database_url.return_value = '******localhost/test'

        from app.mobile.schemas.auth import MobileAuthResponse, MobileAuthUserInfo

        mock_resolve.return_value = MobileAuthResponse(
            subscription_url='https://example.com/sub/xyz',
            user=MobileAuthUserInfo(
                telegram_id=123456,
                first_name='Ivan',
                last_name='Petrov',
                username='ivanp',
            ),
            is_new_user=False,
            has_subscription=True,
        )

        result = await auth_check(token='a' * 32)

    assert isinstance(result, MobileAuthCheckResponse)
    assert result.status == 'verified'
    assert result.auth is not None
    assert result.auth.user.telegram_id == 123456
    assert result.auth.subscription_url == 'https://example.com/sub/xyz'
    assert result.auth.has_subscription is True


@pytest.mark.asyncio
async def test_auth_check_pending_when_telegram_id_missing():
    """If verified token has no telegram_id yet, should stay pending."""
    token_data = {'status': 'verified'}  # missing telegram_id

    with patch('app.mobile.routes.auth.get_auth_token', return_value=token_data):
        result = await auth_check(token='a' * 32)

    assert result.status == 'pending'


# ---------------------------------------------------------------------------
# MOBILE_AUTH_START_PREFIX constant
# ---------------------------------------------------------------------------


def test_start_prefix_value():
    assert MOBILE_AUTH_START_PREFIX == 'mobile_auth_'
