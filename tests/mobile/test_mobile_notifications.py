"""Tests for the mobile GET /notifications endpoint."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


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


# ---------------------------------------------------------------------------
# Tests — /notifications
# ---------------------------------------------------------------------------
# Note: user lookup / "unknown user" now lives entirely in
# get_current_cabinet_user (Bearer JWT dependency) — get_notifications itself
# only ever receives an already-resolved User, so there's no 404 case here.


@pytest.mark.asyncio
async def test_get_notifications_empty_store():
    from app.mobile.routes.notifications import get_notifications

    with patch('app.mobile.routes.notifications.mobile_notification_store') as mock_store:
        mock_store.get_active.return_value = []
        result = await get_notifications(user=_make_user())

    assert result.notifications == []


@pytest.mark.asyncio
async def test_get_notifications_returns_items():
    from app.mobile.routes.notifications import get_notifications

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

    with patch('app.mobile.routes.notifications.mobile_notification_store') as mock_store:
        mock_store.get_active.return_value = pending_notifs
        result = await get_notifications(user=_make_user())

    assert len(result.notifications) == 1
    n = result.notifications[0]
    assert n.id == 'maintenance_01'
    assert n.title == 'Технические работы'
    assert n.severity == 'warning'
    assert n.type == 'persistent'
