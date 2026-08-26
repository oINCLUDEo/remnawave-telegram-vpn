"""Продление подписки на тарифе всегда возвращает тарифный лимит трафика.

Регрессия на протечку grace-капа: вебхук панели записывал
RESERVE_GRACE_TRAFFIC_GB в subscription.traffic_limit_gb, и обычное продление
(без явного traffic_limit_gb) оставляло это значение навсегда.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.crud.subscription import extend_subscription


def _make_db(tariff):
    db = AsyncMock()
    db.get = AsyncMock(return_value=tariff)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_tariff(traffic_limit_gb: int):
    tariff = MagicMock()
    tariff.id = 2
    tariff.traffic_limit_gb = traffic_limit_gb
    tariff.is_daily = False
    return tariff


def _make_subscription(*, traffic_limit_gb: int, purchased: int = 0, days_left: int = 10):
    sub = MagicMock()
    sub.id = 1597
    sub.tariff_id = 2
    sub.status = 'active'
    sub.is_trial = False
    sub.end_date = datetime.now(UTC) + timedelta(days=days_left)
    sub.traffic_limit_gb = traffic_limit_gb
    sub.purchased_traffic_gb = purchased
    sub.connected_squads = ['squad-a']
    return sub


@pytest.mark.asyncio
async def test_renewal_restores_tariff_traffic_limit_when_not_passed():
    """Протёкший grace-кап (3 ГБ) заменяется лимитом тарифа при продлении."""
    tariff = _make_tariff(50)
    sub = _make_subscription(traffic_limit_gb=3)

    await extend_subscription(_make_db(tariff), sub, 30)

    assert sub.traffic_limit_gb == 50


@pytest.mark.asyncio
async def test_renewal_keeps_purchased_traffic_on_top_of_tariff():
    """Докупленный трафик не теряется — он прибавляется к тарифному лимиту."""
    tariff = _make_tariff(50)
    sub = _make_subscription(traffic_limit_gb=3, purchased=25)

    await extend_subscription(_make_db(tariff), sub, 30)

    assert sub.traffic_limit_gb == 75


@pytest.mark.asyncio
async def test_renewal_restores_unlimited_tariff():
    """Безлимитный тариф (0) не должен оставаться срезанным до grace-капа."""
    tariff = _make_tariff(0)
    sub = _make_subscription(traffic_limit_gb=3)

    await extend_subscription(_make_db(tariff), sub, 30)

    assert sub.traffic_limit_gb == 0


@pytest.mark.asyncio
async def test_explicit_traffic_limit_still_wins():
    """Явно переданный лимит имеет приоритет — авто-подстановка не вмешивается."""
    tariff = _make_tariff(50)
    sub = _make_subscription(traffic_limit_gb=3)

    await extend_subscription(_make_db(tariff), sub, 30, traffic_limit_gb=8)

    assert sub.traffic_limit_gb == 8
