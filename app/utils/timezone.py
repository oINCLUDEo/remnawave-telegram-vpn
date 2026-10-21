"""Timezone utilities for consistent local time handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import structlog

from app.config import settings


logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_local_timezone() -> ZoneInfo:
    """Return the configured local timezone.

    Falls back to UTC if the configured timezone cannot be loaded. The
    fallback is logged once and cached for subsequent calls.
    """

    tz_name = settings.TIMEZONE

    try:
        return ZoneInfo(tz_name)
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.warning("⚠️ Не удалось загрузить временную зону '': . Используем UTC.", tz_name=tz_name, exc=exc)
        return ZoneInfo('UTC')


def panel_datetime_to_utc(dt: datetime) -> datetime:
    """Convert a panel datetime to aware UTC.

    Panel API returns local time with a misleading UTC offset (+00:00 / Z).
    This strips the offset, interprets the raw value as panel-local time,
    then converts to aware UTC for database storage.
    """
    naive = dt
    localized = naive.replace(tzinfo=get_local_timezone())
    return localized.astimezone(ZoneInfo('UTC'))


def to_local_datetime(dt: datetime | None) -> datetime | None:
    """Convert a datetime value to the configured local timezone."""

    if dt is None:
        return None

    aware_dt = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return aware_dt.astimezone(get_local_timezone())


def format_local_datetime(
    dt: datetime | None,
    fmt: str = '%Y-%m-%d %H:%M:%S %Z',
    na_placeholder: str = 'N/A',
) -> str:
    """Format a datetime value in the configured local timezone."""

    localized = to_local_datetime(dt)
    if localized is None:
        return na_placeholder
    return localized.strftime(fmt)


def is_quiet_hours(now: datetime | None = None) -> bool:
    """Return True while local time is inside the notification quiet window.

    The window is [START, END) in the configured TIMEZONE and may wrap past
    midnight (22 → 10). START == END means there is no quiet window.
    """

    if not settings.NOTIFICATIONS_QUIET_HOURS_ENABLED:
        return False

    start = settings.NOTIFICATIONS_QUIET_HOURS_START
    end = settings.NOTIFICATIONS_QUIET_HOURS_END
    if start == end:
        return False

    hour = to_local_datetime(now or datetime.now(UTC)).hour
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def quiet_hours_end(now: datetime | None = None) -> datetime:
    """Return the next moment (aware, local tz) when the quiet window ends."""

    local_now = to_local_datetime(now or datetime.now(UTC))
    candidate = local_now.replace(hour=settings.NOTIFICATIONS_QUIET_HOURS_END, minute=0, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate
