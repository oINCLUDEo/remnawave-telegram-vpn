"""Tests for the mobile GET /notifications endpoint."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(status: str = 'active'):
    user = MagicMock()
    user.status = status
    user.telegram_id = 111222333
    user.id = 42
    return user


def _db_ctx(user):
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()
    return mock_db, mock_session_class, mock_engine


# ---------------------------------------------------------------------------
# Tests — /notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_notifications_empty_store():
    from app.mobile.routes.notifications import get_notifications

    mock_db, mock_session_class, mock_engine = _db_ctx(_make_user())

    with (
        patch('app.mobile.routes.notifications.settings') as mock_settings,
        patch('app.mobile.routes.notifications.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.notifications.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.notifications.get_user_by_telegram_id', new_callable=AsyncMock,
              return_value=_make_user()),
        patch('app.mobile.routes.notifications.mobile_notification_store') as mock_store,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_store.get_active.return_value = []

        result = await get_notifications(x_telegram_id=111222333)

    assert result.notifications == []


@pytest.mark.asyncio
async def test_get_notifications_returns_items():
    from app.mobile.routes.notifications import get_notifications

    mock_db, mock_session_class, mock_engine = _db_ctx(_make_user())

    pending_notifs = [
        {
            'id': 'maintenance_01',
            'title': 'Технические работы',
            'body': 'Плановые работы 15 марта.',
            'type': 'persistent',
            'severity': 'warning',
            'auto_dismiss_seconds': 5,
        }
    ]

    with (
        patch('app.mobile.routes.notifications.settings') as mock_settings,
        patch('app.mobile.routes.notifications.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.notifications.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.notifications.get_user_by_telegram_id', new_callable=AsyncMock,
              return_value=_make_user()),
        patch('app.mobile.routes.notifications.mobile_notification_store') as mock_store,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_store.get_active.return_value = pending_notifs

        result = await get_notifications(x_telegram_id=111222333)

    assert len(result.notifications) == 1
    n = result.notifications[0]
    assert n.id == 'maintenance_01'
    assert n.title == 'Технические работы'
    assert n.severity == 'warning'
    assert n.type == 'persistent'


@pytest.mark.asyncio
async def test_get_notifications_returns_404_for_unknown_user():
    from fastapi import HTTPException

    from app.mobile.routes.notifications import get_notifications

    mock_db, mock_session_class, mock_engine = _db_ctx(None)

    with (
        patch('app.mobile.routes.notifications.settings') as mock_settings,
        patch('app.mobile.routes.notifications.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.notifications.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.notifications.get_user_by_telegram_id', new_callable=AsyncMock,
              return_value=None),
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'

        with pytest.raises(HTTPException) as exc_info:
            await get_notifications(x_telegram_id=999)

    assert exc_info.value.status_code == 404
