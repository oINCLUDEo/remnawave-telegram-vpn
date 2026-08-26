"""Сервис расчёта когортной аналитики для выгрузки в Google Sheets.

Готовит данные (заголовки + строки) для 4 листов таблицы:
    - «Когорты»                — базовые когортные метрики по месяцу регистрации
    - «Когорты по источникам»  — те же метрики с разбивкой по источнику (referral/organic)
    - «Retention»              — когортное удержание платящих пользователей (m0..m11);
                                 будущие месяцы — пустые ячейки, а не 0
    - «Доход по юзерам»        — доход и активность по каждому платящему пользователю

Запись в таблицу выполняет bot/export/sheets_sync.py (в рамках обычной синхронизации).

Все даты приводятся к часовому поясу Europe/Moscow перед агрегацией по месяцам.

Важно про лист «Доход по юзерам»: deposits_rub — реальные деньги (пополнения через
платёжные системы из REAL_PAYMENT_METHODS), а subscription_payments_rub — списания
с внутреннего баланса за подписки, которые пользователь ранее пополнил. Эти колонки
пересекаются (одни и те же деньги сначала попадают в депозиты, потом списываются
за подписку), поэтому складывать их между собой нельзя.
"""

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import false, true

from app.database.crud.transaction import REAL_PAYMENT_METHODS
from app.database.models import (
    Subscription,
    SubscriptionConversion,
    SubscriptionStatus,
    Transaction,
    TransactionType,
    User,
)


logger = structlog.get_logger(__name__)

_MOSCOW_TZ = ZoneInfo('Europe/Moscow')

_RETENTION_MONTHS = 12

COHORTS_HEADERS = ['cohort', 'new_users', 'took_trial', 'converted_to_paid', 'active_now', 'revenue_rub']
COHORTS_BY_SOURCE_HEADERS = [
    'cohort',
    'source',
    'new_users',
    'took_trial',
    'converted_to_paid',
    'active_now',
    'revenue_rub',
]
RETENTION_HEADERS = ['cohort', 'payers_total'] + [f'm{i}' for i in range(_RETENTION_MONTHS)]
USER_REVENUE_HEADERS = [
    'user_id',
    'cohort_month',
    'is_referral',
    'deposits_rub',
    'subscription_payments_rub',
    'payments_count',
    'first_payment_at',
    'last_payment_at',
    'days_since_last_payment',
    'is_active_now',
]

# (заголовки, строки) для одного листа
SheetData = tuple[list[str], list[list[Any]]]


class CohortExportService:
    """Готовит когортную аналитику (заголовки + строки) для листов Google Sheets."""

    def __init__(self) -> None:
        self._moscow_tz = _MOSCOW_TZ

    # ---------- публичный API ----------

    async def generate_sheet_data(self, db: AsyncSession) -> dict[str, SheetData]:
        """Формирует данные для 4 листов и возвращает {имя_листа: (headers, rows)}."""
        base = await self._fetch_user_base(db)
        trial_user_ids = await self._fetch_trial_user_ids(db)
        converted_user_ids = await self._fetch_converted_user_ids(db)
        active_user_ids = await self._fetch_active_paid_user_ids(db)
        deposits_by_user = await self._fetch_real_deposits_by_user(db)

        cohorts_rows = self._build_cohorts_rows(
            base,
            trial_user_ids,
            converted_user_ids,
            active_user_ids,
            deposits_by_user,
            by_source=False,
        )
        cohorts_by_source_rows = self._build_cohorts_rows(
            base,
            trial_user_ids,
            converted_user_ids,
            active_user_ids,
            deposits_by_user,
            by_source=True,
        )
        retention_rows = await self._build_retention_rows(db)
        user_revenue_rows = await self._build_user_revenue_rows(db, base, active_user_ids)

        return {
            'Когорты': (COHORTS_HEADERS, cohorts_rows),
            'Когорты по источникам': (COHORTS_BY_SOURCE_HEADERS, cohorts_by_source_rows),
            'Retention': (RETENTION_HEADERS, retention_rows),
            'Доход по юзерам': (USER_REVENUE_HEADERS, user_revenue_rows),
        }

    # ---------- вспомогательные преобразования дат ----------

    def _to_msk(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(self._moscow_tz)

    def _cohort_month(self, dt: datetime) -> str:
        msk = self._to_msk(dt)
        return f'{msk.year:04d}-{msk.month:02d}'

    # ---------- сбор сырых данных ----------

    async def _fetch_user_base(self, db: AsyncSession) -> dict[int, dict]:
        """Базовая информация по всем пользователям: когорта регистрации и источник."""
        rows = (await db.execute(select(User.id, User.created_at, User.referred_by_id))).all()

        base: dict[int, dict] = {}
        for user_id, created_at, referred_by_id in rows:
            base[user_id] = {
                'cohort': self._cohort_month(created_at),
                'is_referral': referred_by_id is not None,
            }
        return base

    async def _fetch_trial_user_ids(self, db: AsyncSession) -> set[int]:
        rows = (
            (await db.execute(select(Subscription.user_id).where(Subscription.is_trial == true()).distinct()))
            .scalars()
            .all()
        )
        return set(rows)

    async def _fetch_converted_user_ids(self, db: AsyncSession) -> set[int]:
        """Пользователи, у которых есть запись о конверсии либо платная подписка."""
        conversion_rows = (await db.execute(select(SubscriptionConversion.user_id).distinct())).scalars().all()
        paid_sub_rows = (
            (await db.execute(select(Subscription.user_id).where(Subscription.is_trial == false()).distinct()))
            .scalars()
            .all()
        )
        return set(conversion_rows) | set(paid_sub_rows)

    async def _fetch_active_paid_user_ids(self, db: AsyncSession) -> set[int]:
        now_utc = datetime.now(UTC)
        rows = (
            (
                await db.execute(
                    select(Subscription.user_id)
                    .where(
                        Subscription.is_trial == false(),
                        Subscription.status == SubscriptionStatus.ACTIVE.value,
                        Subscription.end_date > now_utc,
                    )
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        return set(rows)

    async def _fetch_real_deposits_by_user(self, db: AsyncSession) -> dict[int, float]:
        """Сумма реальных пополнений (в рублях) по каждому пользователю."""
        rows = (
            await db.execute(
                select(Transaction.user_id, func.coalesce(func.sum(func.abs(Transaction.amount_kopeks)), 0))
                .where(
                    Transaction.type == TransactionType.DEPOSIT.value,
                    Transaction.is_completed == true(),
                    Transaction.payment_method.in_(REAL_PAYMENT_METHODS),
                )
                .group_by(Transaction.user_id)
            )
        ).all()
        return {user_id: (kopeks or 0) / 100 for user_id, kopeks in rows}

    async def _fetch_subscription_payments_by_user(
        self,
        db: AsyncSession,
    ) -> dict[int, list[datetime]]:
        """Даты (в UTC) успешных оплат подписки по каждому пользователю."""
        rows = (
            await db.execute(
                select(Transaction.user_id, Transaction.created_at).where(
                    Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
                    Transaction.is_completed == true(),
                )
            )
        ).all()

        result: dict[int, list[datetime]] = defaultdict(list)
        for user_id, created_at in rows:
            result[user_id].append(created_at)
        return result

    # ---------- «Когорты» / «Когорты по источникам» ----------

    def _build_cohorts_rows(
        self,
        base: dict[int, dict],
        trial_user_ids: set[int],
        converted_user_ids: set[int],
        active_user_ids: set[int],
        deposits_by_user: dict[int, float],
        *,
        by_source: bool,
    ) -> list[list[Any]]:
        groups: dict[tuple, list[int]] = defaultdict(list)
        for user_id, info in base.items():
            if by_source:
                source = 'referral' if info['is_referral'] else 'organic'
                key = (info['cohort'], source)
            else:
                key = (info['cohort'],)
            groups[key].append(user_id)

        rows: list[list[Any]] = []
        for key in sorted(groups.keys()):
            user_ids = groups[key]
            new_users = len(user_ids)
            took_trial = sum(1 for uid in user_ids if uid in trial_user_ids)
            converted_to_paid = sum(1 for uid in user_ids if uid in converted_user_ids)
            active_now = sum(1 for uid in user_ids if uid in active_user_ids)
            revenue_rub = round(sum(deposits_by_user.get(uid, 0.0) for uid in user_ids), 2)

            rows.append(list(key) + [new_users, took_trial, converted_to_paid, active_now, revenue_rub])

        return rows

    # ---------- «Retention» ----------

    async def _build_retention_rows(self, db: AsyncSession) -> list[list[Any]]:
        payments_by_user = await self._fetch_subscription_payments_by_user(db)

        first_payment_msk: dict[int, datetime] = {}
        paid_months: dict[int, set[tuple[int, int]]] = {}
        for user_id, dates in payments_by_user.items():
            msk_dates = [self._to_msk(d) for d in dates]
            first_payment_msk[user_id] = min(msk_dates)
            paid_months[user_id] = {(d.year, d.month) for d in msk_dates}

        cohorts: dict[str, list[int]] = defaultdict(list)
        for user_id, first_dt in first_payment_msk.items():
            cohort = f'{first_dt.year:04d}-{first_dt.month:02d}'
            cohorts[cohort].append(user_id)

        now_msk = datetime.now(self._moscow_tz)
        current_month_index = now_msk.year * 12 + (now_msk.month - 1)

        rows: list[list[Any]] = []
        for cohort in sorted(cohorts.keys()):
            user_ids = cohorts[cohort]
            row: list[Any] = [cohort, len(user_ids)]

            cohort_year, cohort_month = (int(part) for part in cohort.split('-'))
            cohort_month_index = cohort_year * 12 + (cohort_month - 1)

            for offset in range(_RETENTION_MONTHS):
                # Месяц ещё не наступил — оставляем ячейку пустой,
                # чтобы отличать "ещё нет данных" от "никто не заплатил".
                if cohort_month_index + offset > current_month_index:
                    row.append('')
                    continue

                retained = 0
                for user_id in user_ids:
                    first_dt = first_payment_msk[user_id]
                    month_index = first_dt.year * 12 + (first_dt.month - 1) + offset
                    target_year, target_month0 = divmod(month_index, 12)
                    target_month = target_month0 + 1
                    if (target_year, target_month) in paid_months[user_id]:
                        retained += 1
                row.append(retained)

            rows.append(row)

        return rows

    # ---------- «Доход по юзерам» ----------

    async def _build_user_revenue_rows(
        self,
        db: AsyncSession,
        base: dict[int, dict],
        active_user_ids: set[int],
    ) -> list[list[Any]]:
        rows = (
            await db.execute(
                select(
                    Transaction.user_id,
                    Transaction.type,
                    Transaction.amount_kopeks,
                    Transaction.created_at,
                    Transaction.payment_method,
                ).where(
                    Transaction.is_completed == true(),
                    (
                        (Transaction.type == TransactionType.DEPOSIT.value)
                        & Transaction.payment_method.in_(REAL_PAYMENT_METHODS)
                    )
                    | (Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value),
                )
            )
        ).all()

        per_user: dict[int, dict] = {}
        for user_id, txn_type, amount_kopeks, created_at, _payment_method in rows:
            entry = per_user.setdefault(
                user_id,
                {
                    'deposits_kopeks': 0,
                    'subscription_payments_kopeks': 0,
                    'payments_count': 0,
                    'first_payment_at': created_at,
                    'last_payment_at': created_at,
                },
            )
            # SUBSCRIPTION_PAYMENT хранится с отрицательным amount_kopeks (списание с баланса),
            # поэтому суммируем модуль — как это делает остальной код (func.abs).
            # payments_count считает только покупки подписок: оплата через баланс порождает
            # пару DEPOSIT + SUBSCRIPTION_PAYMENT, и учёт обеих записей задваивал бы счётчик.
            if txn_type == TransactionType.DEPOSIT.value:
                entry['deposits_kopeks'] += abs(amount_kopeks or 0)
            elif txn_type == TransactionType.SUBSCRIPTION_PAYMENT.value:
                entry['subscription_payments_kopeks'] += abs(amount_kopeks or 0)
                entry['payments_count'] += 1
            entry['first_payment_at'] = min(entry['first_payment_at'], created_at)
            entry['last_payment_at'] = max(entry['last_payment_at'], created_at)

        now_utc = datetime.now(UTC)

        result_rows: list[list[Any]] = []
        for user_id in sorted(per_user.keys()):
            entry = per_user[user_id]
            user_info = base.get(user_id, {'cohort': '', 'is_referral': False})

            last_payment_at = entry['last_payment_at']
            if last_payment_at.tzinfo is None:
                last_payment_at = last_payment_at.replace(tzinfo=UTC)
            days_since_last_payment = (now_utc - last_payment_at).days

            result_rows.append(
                [
                    user_id,
                    user_info['cohort'],
                    int(user_info['is_referral']),
                    round(entry['deposits_kopeks'] / 100, 2),
                    round(entry['subscription_payments_kopeks'] / 100, 2),
                    entry['payments_count'],
                    self._to_msk(entry['first_payment_at']).strftime('%Y-%m-%d %H:%M:%S'),
                    self._to_msk(entry['last_payment_at']).strftime('%Y-%m-%d %H:%M:%S'),
                    days_since_last_payment,
                    int(user_id in active_user_ids),
                ]
            )

        return result_rows


cohort_export_service = CohortExportService()
