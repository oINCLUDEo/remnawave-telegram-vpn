"""Тесты тихих часов для уведомлений (app.utils.timezone)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.config import settings
from app.utils import timezone as tz


MSK = ZoneInfo('Europe/Moscow')


@pytest.fixture(autouse=True)
def moscow_quiet_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tz, 'get_local_timezone', lambda: MSK)
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_ENABLED', True, raising=False)
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_START', 22, raising=False)
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_END', 10, raising=False)


def msk(hour: int, minute: int = 0, day: int = 4) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=MSK).astimezone(UTC)


@pytest.mark.parametrize(
    ('hour', 'expected'),
    [(21, False), (22, True), (23, True), (0, True), (3, True), (9, True), (10, False), (15, False)],
)
def test_window_wraps_past_midnight(hour: int, expected: bool) -> None:
    assert tz.is_quiet_hours(msk(hour, 30)) is expected


def test_window_inside_one_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_START', 1, raising=False)
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_END', 6, raising=False)
    assert tz.is_quiet_hours(msk(0)) is False
    assert tz.is_quiet_hours(msk(1)) is True
    assert tz.is_quiet_hours(msk(5, 59)) is True
    assert tz.is_quiet_hours(msk(6)) is False


def test_disabled_or_empty_window_is_never_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_ENABLED', False, raising=False)
    assert tz.is_quiet_hours(msk(3)) is False

    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_ENABLED', True, raising=False)
    monkeypatch.setattr(settings, 'NOTIFICATIONS_QUIET_HOURS_END', 22, raising=False)
    assert tz.is_quiet_hours(msk(3)) is False


def test_quiet_hours_end_is_next_morning() -> None:
    assert tz.quiet_hours_end(msk(23)) == datetime(2026, 10, 5, 10, tzinfo=MSK)
    assert tz.quiet_hours_end(msk(3)) == datetime(2026, 10, 4, 10, tzinfo=MSK)
