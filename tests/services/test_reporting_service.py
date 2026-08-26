"""Тесты для новой логики в app/services/reporting_service.py:

- когортная конверсия триалов недельной давности (_get_weekly_trial_conversion_stats)
- метрика "с подпиской, но без трафика" вместо connected_squads (_get_user_usage_stats)
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.reporting_service import ReportingService


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalar(self):
        if not self._rows:
            return None
        row = self._rows[0]
        return row[0] if isinstance(row, tuple) else row


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, *_args, **_kwargs):
        return self._results.pop(0)


async def test_weekly_trial_conversion_counts_conversions_within_7_days():
    """Триал, конвертированный в течение 7 дней после создания, должен попасть в конверсии."""
    service = ReportingService()

    start_utc = datetime(2026, 7, 8, tzinfo=UTC)
    end_utc = datetime(2026, 7, 9, tzinfo=UTC)
    # Когорта триалов: [start-7d, end-7d) = [2026-07-01, 2026-07-02)
    trial_created_at = datetime(2026, 7, 1, 10, tzinfo=UTC)

    trial_rows = [
        (1, trial_created_at),
        (2, trial_created_at),
    ]
    # user 1 конвертировался через 3 дня (в пределах 7 дней) - засчитывается
    # user 2 конвертировался через 10 дней (позже 7 дней) - не засчитывается
    conversion_rows = [
        (1, trial_created_at + timedelta(days=3)),
        (2, trial_created_at + timedelta(days=10)),
    ]

    session = _FakeSession([_FakeResult(trial_rows), _FakeResult(conversion_rows)])

    result = await service._get_weekly_trial_conversion_stats(session, start_utc, end_utc)

    assert result['weekly_trial_cohort_size'] == 2
    assert result['weekly_trial_conversions'] == 1
    assert result['weekly_conversion_rate'] == 50.0


async def test_weekly_trial_conversion_ignores_conversions_before_trial_creation():
    """
    Конверсия, случившаяся ДО создания триала (повторный триал после старой оплаты),
    не должна засчитываться как конверсия этого триала.
    """
    service = ReportingService()

    start_utc = datetime(2026, 7, 8, tzinfo=UTC)
    end_utc = datetime(2026, 7, 9, tzinfo=UTC)
    trial_created_at = datetime(2026, 7, 1, 10, tzinfo=UTC)

    trial_rows = [(1, trial_created_at)]
    # Старая конверсия за месяц до создания нового триала - не должна учитываться.
    conversion_rows = [(1, trial_created_at - timedelta(days=30))]

    session = _FakeSession([_FakeResult(trial_rows), _FakeResult(conversion_rows)])

    result = await service._get_weekly_trial_conversion_stats(session, start_utc, end_utc)

    assert result['weekly_trial_cohort_size'] == 1
    assert result['weekly_trial_conversions'] == 0
    assert result['weekly_conversion_rate'] == 0.0


async def test_weekly_trial_conversion_empty_cohort_returns_zero():
    service = ReportingService()
    start_utc = datetime(2026, 7, 8, tzinfo=UTC)
    end_utc = datetime(2026, 7, 9, tzinfo=UTC)

    session = _FakeSession([_FakeResult([])])

    result = await service._get_weekly_trial_conversion_stats(session, start_utc, end_utc)

    assert result == {
        'weekly_trial_cohort_size': 0,
        'weekly_trial_conversions': 0,
        'weekly_conversion_rate': 0.0,
    }


async def test_get_user_usage_stats_uses_lifetime_traffic_not_connected_squads():
    """
    Метрика 'без трафика' должна основываться на User.lifetime_used_traffic_bytes,
    а не на Subscription.connected_squads (старая логика).
    """
    service = ReportingService()

    active_paid_result = _FakeResult([(3,)])
    never_connected_result = _FakeResult([(2,)])

    session = _FakeSession([active_paid_result, never_connected_result])

    result = await service._get_user_usage_stats(session)

    assert result['active_paid_users'] == 3
    assert result['never_connected_users'] == 2
