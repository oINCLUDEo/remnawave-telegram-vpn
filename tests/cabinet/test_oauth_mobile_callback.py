"""Tests for the mobile OAuth redirect callback (GET /{provider}/mobile-callback).

This is the real browser-facing redirect_uri for the Flutter app's Google
sign-in — unlike oauth_callback (JSON API), every path here must redirect
back into the app via ulyavpn:// instead of raising, since the caller is a
real browser with no other way back to the app.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.cabinet.routes.oauth import oauth_mobile_callback


def _mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


def _assert_error_redirect(response, expected_error: str | None = None):
    from fastapi.responses import RedirectResponse

    assert isinstance(response, RedirectResponse)
    location = response.headers['location']
    assert location.startswith('ulyavpn://oauth/done?error=')
    if expected_error:
        assert expected_error in location


@pytest.mark.asyncio
async def test_provider_error_redirects_to_app_with_error():
    response = await oauth_mobile_callback(
        provider='google', code=None, state=None, error='access_denied', db=_mock_db()
    )
    _assert_error_redirect(response, 'access_denied')


@pytest.mark.asyncio
async def test_missing_code_or_state_redirects_with_error():
    response = await oauth_mobile_callback(provider='google', code=None, state='some-state', db=_mock_db())
    _assert_error_redirect(response, 'missing_code_or_state')


@pytest.mark.asyncio
async def test_invalid_state_redirects_with_error():
    with patch('app.cabinet.routes.oauth.validate_oauth_state', new_callable=AsyncMock, return_value=None):
        response = await oauth_mobile_callback(provider='google', code='abc', state='bad-state', db=_mock_db())
    _assert_error_redirect(response, 'invalid_state')


@pytest.mark.asyncio
async def test_linking_flow_state_is_rejected():
    """A state token from the account-linking flow must not be usable here —
    otherwise a linking attempt could be hijacked into a full login."""
    state_data = {'provider': 'google', 'linking': 'true', 'user_id': '42'}
    with patch('app.cabinet.routes.oauth.validate_oauth_state', new_callable=AsyncMock, return_value=state_data):
        response = await oauth_mobile_callback(provider='google', code='abc', state='link-state', db=_mock_db())
    _assert_error_redirect(response, 'invalid_state')


@pytest.mark.asyncio
async def test_non_mobile_login_state_is_rejected():
    """A state token from the web login flow (no mobile=true marker) must not
    be accepted here — it was authorized for the web cabinet's redirect_uri,
    not this one."""
    state_data = {'provider': 'google'}
    with patch('app.cabinet.routes.oauth.validate_oauth_state', new_callable=AsyncMock, return_value=state_data):
        response = await oauth_mobile_callback(provider='google', code='abc', state='web-state', db=_mock_db())
    _assert_error_redirect(response, 'invalid_state')


@pytest.mark.asyncio
async def test_exchange_failure_redirects_with_error():
    state_data = {'provider': 'google', 'mobile': 'true'}
    mock_provider = MagicMock()
    mock_provider.exchange_code = AsyncMock(side_effect=Exception('boom'))

    with (
        patch('app.cabinet.routes.oauth.validate_oauth_state', new_callable=AsyncMock, return_value=state_data),
        patch('app.cabinet.routes.oauth.get_provider', return_value=mock_provider),
    ):
        response = await oauth_mobile_callback(provider='google', code='abc', state='mobile-state', db=_mock_db())
    _assert_error_redirect(response, 'exchange_failed')


@pytest.mark.asyncio
async def test_provider_not_configured_redirects_with_error():
    state_data = {'provider': 'google', 'mobile': 'true'}
    with (
        patch('app.cabinet.routes.oauth.validate_oauth_state', new_callable=AsyncMock, return_value=state_data),
        patch('app.cabinet.routes.oauth.get_provider', return_value=None),
    ):
        response = await oauth_mobile_callback(provider='google', code='abc', state='mobile-state', db=_mock_db())
    _assert_error_redirect(response, 'provider_unavailable')


@pytest.mark.asyncio
async def test_successful_login_redirects_with_token():
    from fastapi.responses import RedirectResponse

    state_data = {'provider': 'google', 'mobile': 'true'}
    mock_provider = MagicMock()
    mock_provider.exchange_code = AsyncMock(return_value={'access_token': 'gtok'})
    mock_provider.get_user_info = AsyncMock(return_value=MagicMock(
        provider_id='g-123', email='a@b.com', email_verified=True,
        first_name='A', last_name='B', username='ab',
    ))

    mock_user = MagicMock()
    mock_user.id = 7

    with (
        patch('app.cabinet.routes.oauth.validate_oauth_state', new_callable=AsyncMock, return_value=state_data),
        patch('app.cabinet.routes.oauth.get_provider', return_value=mock_provider),
        patch(
            'app.cabinet.routes.oauth._resolve_or_create_oauth_user',
            new_callable=AsyncMock,
            return_value=(mock_user, False),
        ),
        patch('app.cabinet.routes.oauth.create_auto_login_token', return_value='short-lived-jwt'),
    ):
        db = _mock_db()
        response = await oauth_mobile_callback(provider='google', code='abc', state='mobile-state', db=db)

    assert isinstance(response, RedirectResponse)
    assert response.headers['location'] == 'ulyavpn://oauth/done?token=short-lived-jwt'
    db.commit.assert_awaited()
