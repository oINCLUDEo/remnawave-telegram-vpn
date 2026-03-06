"""Tests for the mobile API auth endpoint."""

from __future__ import annotations

import hashlib
import hmac
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.mobile.routes.auth import _validate_telegram_widget_data, auth_telegram_widget, get_auth_widget_page
from app.mobile.schemas.auth import MobileTelegramWidgetAuthRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign_widget_data(data: dict, bot_token: str) -> str:
    """Sign Telegram Login Widget data the same way Telegram does."""
    check_data = {k: v for k, v in data.items() if v is not None}
    check_data.pop('hash', None)
    data_check_arr = [f'{k}={v}' for k, v in sorted(check_data.items())]
    data_check_string = '\n'.join(data_check_arr)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def _valid_request(bot_token: str = 'test-mobile-token') -> dict:
    data = {
        'id': 123456789,
        'first_name': 'Ivan',
        'last_name': 'Petrov',
        'username': 'ivanp',
        'auth_date': int(time.time()),
        'photo_url': None,
    }
    data['hash'] = _sign_widget_data(data, bot_token)
    return data


def _make_mock_db(subscription_url: str | None = None, user_status: str = 'active') -> MagicMock:
    """Build a mock AsyncSession that returns a user with an optional subscription."""
    mock_subscription = MagicMock()
    mock_subscription.subscription_url = subscription_url

    mock_user = MagicMock()
    mock_user.status = user_status
    mock_user.subscription = mock_subscription if subscription_url else None

    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db._mock_user = mock_user  # stash for patching
    return mock_db


# ---------------------------------------------------------------------------
# Unit tests: _validate_telegram_widget_data
# ---------------------------------------------------------------------------


def test_valid_widget_data_passes():
    token = 'abc123'
    data = _valid_request(token)
    assert _validate_telegram_widget_data(data, token) is True


def test_invalid_hash_fails():
    token = 'abc123'
    data = _valid_request(token)
    data['hash'] = 'deadbeef' * 8
    assert _validate_telegram_widget_data(data, token) is False


def test_missing_hash_fails():
    token = 'abc123'
    data = _valid_request(token)
    del data['hash']
    assert _validate_telegram_widget_data(data, token) is False


def test_expired_auth_date_fails():
    token = 'abc123'
    data = _valid_request(token)
    # Force an old timestamp (> 86400 seconds ago)
    data['auth_date'] = int(time.time()) - 90000
    data['hash'] = _sign_widget_data(data, token)
    assert _validate_telegram_widget_data(data, token) is False


def test_wrong_bot_token_fails():
    data = _valid_request('correct-token')
    assert _validate_telegram_widget_data(data, 'wrong-token') is False


# ---------------------------------------------------------------------------
# Widget HTML page endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_widget_page_returns_html_with_bot_username():
    with patch('app.mobile.routes.auth.settings') as mock_settings:
        mock_settings.is_mobile_auth_enabled.return_value = True
        mock_settings.MOBILE_AUTH_BOT_USERNAME = 'MyTestBot'

        response = await get_auth_widget_page()

    assert response.status_code == 200
    assert 'MyTestBot' in response.body.decode()
    assert 'telegram-widget.js' in response.body.decode()


@pytest.mark.asyncio
async def test_widget_page_returns_error_when_not_configured():
    with patch('app.mobile.routes.auth.settings') as mock_settings:
        mock_settings.is_mobile_auth_enabled.return_value = False
        mock_settings.MOBILE_AUTH_BOT_USERNAME = None

        response = await get_auth_widget_page()

    assert response.status_code == 200
    body = response.body.decode()
    assert 'telegram-widget.js' not in body
    assert 'не настроена' in body or 'Авторизация не настроена' in body


# ---------------------------------------------------------------------------
# Auth endpoint — mocking the whole _get_or_create_user helper
# ---------------------------------------------------------------------------


def _make_session_factory(mock_user: MagicMock) -> MagicMock:
    """Returns a mock sessionmaker-like callable that yields mock_user via context mgr."""
    mock_db = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda u, attrs: None)
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()
    return mock_session_class, mock_engine, mock_db


@pytest.mark.asyncio
async def test_auth_returns_503_when_bot_token_not_configured():
    from fastapi import HTTPException

    req_data = _valid_request()
    request = MobileTelegramWidgetAuthRequest(**req_data)

    with patch('app.mobile.routes.auth.settings') as mock_settings:
        mock_settings.get_mobile_auth_bot_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await auth_telegram_widget(request)

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_auth_returns_401_for_invalid_signature():
    from fastapi import HTTPException

    req_data = _valid_request('correct-token')
    req_data['hash'] = 'bad' * 20
    request = MobileTelegramWidgetAuthRequest(**req_data)

    with patch('app.mobile.routes.auth.settings') as mock_settings:
        mock_settings.get_mobile_auth_bot_token.return_value = 'correct-token'

        with pytest.raises(HTTPException) as exc_info:
            await auth_telegram_widget(request)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_returns_subscription_url_for_existing_user():
    token = 'mobile-test-token'
    req_data = _valid_request(token)
    request = MobileTelegramWidgetAuthRequest(**req_data)

    mock_subscription = MagicMock()
    mock_subscription.subscription_url = 'https://example.com/sub/abc123'

    mock_user = MagicMock()
    mock_user.status = 'active'
    mock_user.subscription = mock_subscription

    mock_session_class, mock_engine, mock_db = _make_session_factory(mock_user)

    # After db.refresh the user's subscription attr must be set.
    async def _set_sub(u, attrs):
        u.subscription = mock_subscription

    mock_db.refresh = AsyncMock(side_effect=_set_sub)

    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.auth.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.auth._get_or_create_user', return_value=(mock_user, False)),
    ):
        mock_settings.get_mobile_auth_bot_token.return_value = token
        mock_settings.get_database_url.return_value = 'postgresql+asyncpg://u:p@localhost/test'

        result = await auth_telegram_widget(request)

    assert result.has_subscription is True
    assert result.subscription_url == 'https://example.com/sub/abc123'
    assert result.is_new_user is False
    assert result.user.telegram_id == req_data['id']


@pytest.mark.asyncio
async def test_auth_creates_new_user_when_not_found():
    token = 'mobile-test-token'
    req_data = _valid_request(token)
    request = MobileTelegramWidgetAuthRequest(**req_data)

    mock_user = MagicMock()
    mock_user.status = 'active'
    mock_user.subscription = None

    mock_session_class, mock_engine, mock_db = _make_session_factory(mock_user)

    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.auth.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.auth._get_or_create_user', return_value=(mock_user, True)),
    ):
        mock_settings.get_mobile_auth_bot_token.return_value = token
        mock_settings.get_database_url.return_value = 'postgresql+asyncpg://u:p@localhost/test'

        result = await auth_telegram_widget(request)

    assert result.is_new_user is True
    assert result.has_subscription is False
    assert result.subscription_url is None


@pytest.mark.asyncio
async def test_auth_returns_403_for_banned_user():
    from fastapi import HTTPException

    token = 'mobile-test-token'
    req_data = _valid_request(token)
    request = MobileTelegramWidgetAuthRequest(**req_data)

    mock_session_class, mock_engine, mock_db = _make_session_factory(MagicMock())

    with (
        patch('app.mobile.routes.auth.settings') as mock_settings,
        patch('app.mobile.routes.auth.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.auth.sessionmaker', return_value=mock_session_class),
        patch(
            'app.mobile.routes.auth._get_or_create_user',
            side_effect=HTTPException(status_code=403, detail='Учётная запись заблокирована'),
        ),
    ):
        mock_settings.get_mobile_auth_bot_token.return_value = token
        mock_settings.get_database_url.return_value = 'postgresql+asyncpg://u:p@localhost/test'

        with pytest.raises(HTTPException) as exc_info:
            await auth_telegram_widget(request)

    assert exc_info.value.status_code == 403
