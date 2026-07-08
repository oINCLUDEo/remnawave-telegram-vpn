"""Тесты для сервиса когортной аналитики (app/services/cohort_export_service.py).

Сервис возвращает данные листов Google Sheets как (headers, rows).
"""

import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.cohort_export_service import (
    COHORTS_BY_SOURCE_HEADERS,
    COHORTS_HEADERS,
    RETENTION_HEADERS,
    USER_REVENUE_HEADERS,
    CohortExportService,
)


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        # Одностолбцовые select() возвращают "голые" значения, а не кортежи.
        flat = [row[0] if isinstance(row, tuple) else row for row in self._rows]
        return _FakeScalars(flat)

    def scalar(self):
        if not self._rows:
            return None
        row = self._rows[0]
        return row[0] if isinstance(row, tuple) else row


class _FakeSession:
    """Мок AsyncSession, отдающий заранее заданные результаты по очереди вызовов execute()."""

    def __init__(self, results):
        self._results = list(results)

    async def execute(self, *_args, **_kwargs):
        return self._results.pop(0)


def _dt(year, month, day=15, hour=12, tz=UTC):
    return datetime(year, month, day, hour, tzinfo=tz)


def _as_dicts(headers: list[str], rows: list[list]) -> list[dict]:
    return [dict(zip(headers, row, strict=True)) for row in rows]


def test_build_cohorts_rows_basic_aggregation():
    """Проверяем базовые метрики по когорте: new_users/took_trial/converted/active/revenue."""
    service = CohortExportService()

    base = {
        1: {'cohort': '2026-01', 'is_referral': False},
        2: {'cohort': '2026-01', 'is_referral': True},
        3: {'cohort': '2026-02', 'is_referral': False},
    }
    trial_user_ids = {1, 3}
    converted_user_ids = {1}
    active_user_ids = {1}
    deposits_by_user = {1: 500.0, 2: 100.0}

    rows = service._build_cohorts_rows(
        base, trial_user_ids, converted_user_ids, active_user_ids, deposits_by_user, by_source=False
    )
    parsed = _as_dicts(COHORTS_HEADERS, rows)

    jan_row = next(r for r in parsed if r['cohort'] == '2026-01')
    assert jan_row['new_users'] == 2
    assert jan_row['took_trial'] == 1
    assert jan_row['converted_to_paid'] == 1
    assert jan_row['active_now'] == 1
    assert jan_row['revenue_rub'] == 600.0

    feb_row = next(r for r in parsed if r['cohort'] == '2026-02')
    assert feb_row['new_users'] == 1
    assert feb_row['took_trial'] == 1
    assert feb_row['revenue_rub'] == 0.0


def test_build_cohorts_rows_by_source_splits_referral_and_organic():
    service = CohortExportService()

    base = {
        1: {'cohort': '2026-01', 'is_referral': False},
        2: {'cohort': '2026-01', 'is_referral': True},
    }

    rows = service._build_cohorts_rows(base, set(), set(), set(), {}, by_source=True)
    parsed = _as_dicts(COHORTS_BY_SOURCE_HEADERS, rows)

    sources = {(r['cohort'], r['source']): r['new_users'] for r in parsed}
    assert sources[('2026-01', 'organic')] == 1
    assert sources[('2026-01', 'referral')] == 1


async def test_build_retention_rows_counts_month_offsets():
    """Пользователь платил в месяц когорты и через 2 месяца -> m0 и m2 должны быть учтены, m1 - нет."""
    service = CohortExportService()

    rows = [
        (1, _dt(2026, 1)),  # первый платеж -> когорта 2026-01, m0
        (1, _dt(2026, 3)),  # платеж через 2 месяца -> m2
        (2, _dt(2026, 2)),  # другой юзер, когорта 2026-02, m0
    ]
    db = _FakeSession([_FakeResult(rows)])

    retention_rows = await service._build_retention_rows(db)
    parsed = _as_dicts(RETENTION_HEADERS, retention_rows)

    jan_cohort = next(r for r in parsed if r['cohort'] == '2026-01')
    assert jan_cohort['payers_total'] == 1
    assert jan_cohort['m0'] == 1
    assert jan_cohort['m1'] == 0
    assert jan_cohort['m2'] == 1

    feb_cohort = next(r for r in parsed if r['cohort'] == '2026-02')
    assert feb_cohort['payers_total'] == 1
    assert feb_cohort['m0'] == 1


async def test_build_retention_rows_future_months_are_blank():
    """Для месяцев, которые ещё не наступили, ячейка должна быть пустой, а не 0."""
    from datetime import datetime as _datetime
    from zoneinfo import ZoneInfo as _ZoneInfo

    service = CohortExportService()

    now_msk = _datetime.now(_ZoneInfo('Europe/Moscow'))
    # Платёж в текущем месяце МСК -> когорта = текущий месяц, m0 наступил, m1..m11 - ещё нет.
    rows = [(1, now_msk)]
    db = _FakeSession([_FakeResult(rows)])

    retention_rows = await service._build_retention_rows(db)
    parsed = _as_dicts(RETENTION_HEADERS, retention_rows)

    assert len(parsed) == 1
    row = parsed[0]
    assert row['m0'] == 1
    for i in range(1, 12):
        assert row[f'm{i}'] == '', f'm{i} should be blank for a future month'


async def test_build_user_revenue_rows_aggregates_deposits_and_payments():
    service = CohortExportService()

    from app.database.models import TransactionType

    rows = [
        (1, TransactionType.DEPOSIT.value, 10000, _dt(2026, 1, 1), 'yookassa'),
        # SUBSCRIPTION_PAYMENT хранится в БД с отрицательной суммой (списание с баланса),
        # см. app/database/crud/transaction.py: stored_amount = -amount_kopeks.
        # Сервис должен суммировать модуль, а не сырое значение.
        (1, TransactionType.SUBSCRIPTION_PAYMENT.value, -5000, _dt(2026, 1, 10), None),
        (2, TransactionType.DEPOSIT.value, 2000, _dt(2026, 2, 1), 'tribute'),
    ]
    db = _FakeSession([_FakeResult(rows)])

    base = {
        1: {'cohort': '2025-12', 'is_referral': False},
        2: {'cohort': '2026-02', 'is_referral': True},
    }
    active_user_ids = {2}

    revenue_rows = await service._build_user_revenue_rows(db, base, active_user_ids)
    parsed = _as_dicts(USER_REVENUE_HEADERS, revenue_rows)

    user1 = next(r for r in parsed if r['user_id'] == 1)
    assert user1['cohort_month'] == '2025-12'
    assert user1['is_referral'] == 0
    assert user1['deposits_rub'] == 100.0
    assert user1['subscription_payments_rub'] == 50.0
    # Только SUBSCRIPTION_PAYMENT: пополнение + списание за подписку = одна оплата, не две.
    assert user1['payments_count'] == 1
    assert user1['is_active_now'] == 0

    user2 = next(r for r in parsed if r['user_id'] == 2)
    assert user2['deposits_rub'] == 20.0
    assert user2['payments_count'] == 0
    assert user2['is_active_now'] == 1


async def test_generate_sheet_data_produces_four_named_sheets():
    """Смоук-тест: все 4 листа формируются с корректными заголовками и ровными строками."""
    service = CohortExportService()

    from app.database.models import TransactionType

    user_base_rows = [(1, _dt(2026, 1), None)]
    trial_ids_rows = [1]
    conversion_ids_rows: list = []
    paid_sub_ids_rows: list = []
    active_ids_rows: list = []
    deposits_rows = [(1, 10000)]
    subscription_payment_rows = [(1, _dt(2026, 1, 5))]
    user_revenue_rows = [(1, TransactionType.DEPOSIT.value, 10000, _dt(2026, 1, 5), 'yookassa')]

    db = _FakeSession(
        [
            _FakeResult(user_base_rows),
            _FakeResult(trial_ids_rows),
            _FakeResult(conversion_ids_rows),
            _FakeResult(paid_sub_ids_rows),
            _FakeResult(active_ids_rows),
            _FakeResult(deposits_rows),
            _FakeResult(subscription_payment_rows),
            _FakeResult(user_revenue_rows),
        ]
    )

    sheets = await service.generate_sheet_data(db)

    assert set(sheets.keys()) == {'Когорты', 'Когорты по источникам', 'Retention', 'Доход по юзерам'}
    assert sheets['Когорты'][0] == COHORTS_HEADERS
    assert sheets['Когорты по источникам'][0] == COHORTS_BY_SOURCE_HEADERS
    assert sheets['Retention'][0] == RETENTION_HEADERS
    assert sheets['Доход по юзерам'][0] == USER_REVENUE_HEADERS
    for sheet_name, (headers, rows) in sheets.items():
        assert headers, f'{sheet_name}: headers are empty'
        for row in rows:
            assert len(row) == len(headers), f'{sheet_name}: row width != headers width'
