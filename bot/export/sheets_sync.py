"""
Google Sheets daily sync module.

Entry point: run_daily_sync(db_session) -> None

Schema mapping (actual DB → spec concepts):
  transactions            ← payments / balance_events
  transactions.type       ← SUBSCRIPTION_PAYMENT, DEPOSIT, REFERRAL_REWARD, …
  transactions.amount_kopeks  ← negative for SUBSCRIPTION_PAYMENT, positive for DEPOSIT
  transactions.payment_method ← 'telegram_stars' | 'balance' | <real gateway> | None
  users.referred_by_id    ← referred_by
  users.has_had_paid_subscription ← is_paid
  users.created_at        ← registered_at
  subscriptions + tariffs ← plan / tariff / period
  subscription_conversions ← new-vs-renewal signal
  referral_earnings       ← referral commission amounts
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.crud.transaction import REAL_PAYMENT_METHODS
from app.database.models import (
    ReferralEarning,
    Subscription,
    SubscriptionConversion,
    SubscriptionStatus,
    Transaction,
    TransactionType,
    User,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------

SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS_JSON_PATH: str = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH", "")
STARS_RUB_RATE: float = float(os.getenv("SHEETS_STARS_RUB_RATE", "1.3"))

SHEET_TRANSACTIONS = "Транзакции"
SHEET_BY_MONTHS = "По месяцам"
SHEET_METRICS = "Метрики"

# Payment methods that represent real external cash inflows.
# Imported from existing crud to stay in sync with the rest of the codebase.
_REAL_METHODS: set[str] = set(REAL_PAYMENT_METHODS)

# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------

def _r2(v: float) -> float:
    """Round to 2 decimal places."""
    return round(v, 2)


def _r1(v: float) -> float:
    """Round to 1 decimal place."""
    return round(v, 1)


def _kopeks_rub(kopeks: int) -> float:
    """Absolute kopeks → rubles, 2 dp."""
    return _r2(abs(kopeks) / 100.0)


def _detect_method(payment_method: Optional[str]) -> str:
    """Map payment_method value to display string for sheet column E."""
    if payment_method == "telegram_stars":
        return "Stars"
    if payment_method == "balance":
        return "Баланс"
    if payment_method is None:
        return "—"
    return "RUB"


def _month_bounds_utc(today: date) -> tuple[datetime, datetime]:
    """Return (month_start_utc, exclusive_end_utc_for_today)."""
    month_start = datetime(today.year, today.month, 1, tzinfo=UTC)
    tomorrow = datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)
    return month_start, tomorrow


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------

async def _fetch_transactions(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> list[Transaction]:
    """
    Fetch completed SUBSCRIPTION_PAYMENT and DEPOSIT transactions for the month.

    REFERRAL_REWARD, POLL_REWARD, WITHDRAWAL, REFUND etc. are intentionally excluded:
    - REFERRAL_REWARD: balance credit (liability), not a cash inflow — spec §CRITICAL
    - WITHDRAWAL: outbound payment to user, tracked separately
    - REFUND / FAILED_REFUND: reversals, not normal revenue
    """
    result = await session.execute(
        select(Transaction)
        .options(selectinload(Transaction.user))
        .where(
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
            Transaction.type.in_([
                TransactionType.SUBSCRIPTION_PAYMENT.value,
                TransactionType.DEPOSIT.value,
            ]),
        )
        .order_by(Transaction.created_at)
    )
    return list(result.scalars().all())


async def _fetch_subscriptions_for_users(
    session: AsyncSession,
    user_ids: set[int],
) -> dict[int, list[Subscription]]:
    """Return subscriptions grouped by user_id, with tariff eager-loaded."""
    if not user_ids:
        return {}
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.tariff))
        .where(Subscription.user_id.in_(user_ids))
        .order_by(Subscription.created_at)
    )
    by_user: dict[int, list[Subscription]] = {}
    for sub in result.scalars().all():
        by_user.setdefault(sub.user_id, []).append(sub)
    return by_user


async def _fetch_converted_user_ids(
    session: AsyncSession,
    user_ids: set[int],
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> set[int]:
    """
    Return user IDs that had a trial→paid conversion this month.
    Used to classify SUBSCRIPTION_PAYMENT as 'new' vs 'renewal'.
    """
    if not user_ids:
        return set()
    result = await session.execute(
        select(SubscriptionConversion.user_id).where(
            SubscriptionConversion.user_id.in_(user_ids),
            SubscriptionConversion.converted_at >= month_start_utc,
            SubscriptionConversion.converted_at < day_end_utc,
        )
    )
    return {row[0] for row in result.all()}


async def _count_active_paying(session: AsyncSession) -> int:
    """Count users with at least one active non-trial subscription right now."""
    now_utc = datetime.now(UTC)
    result = await session.execute(
        select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.is_trial.is_(False),
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.end_date > now_utc,
        )
    )
    return int(result.scalar() or 0)


async def _count_new_paying(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> int:
    """
    New paying users this month =
      trial→paid conversions + directly-paid subscriptions (is_trial=False, new this month).
    """
    conversions = int(
        (
            await session.execute(
                select(func.count(SubscriptionConversion.id)).where(
                    SubscriptionConversion.converted_at >= month_start_utc,
                    SubscriptionConversion.converted_at < day_end_utc,
                )
            )
        ).scalar()
        or 0
    )
    from sqlalchemy.sql import false

    direct_new = int(
        (
            await session.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.created_at >= month_start_utc,
                    Subscription.created_at < day_end_utc,
                    Subscription.is_trial == false(),
                )
            )
        ).scalar()
        or 0
    )
    return conversions + direct_new


async def _count_churned(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
    today: date,
) -> int:
    """
    Churned = users who had a completed SUBSCRIPTION_PAYMENT in months M-3..M-1
    but have NO completed payment in month M AND no active subscription at month-end.

    Approximates 3 prior months as 91 days before month_start.
    """
    prior_start_utc = month_start_utc - timedelta(days=91)

    # Users who paid in prior 3 months
    prior_result = await session.execute(
        select(func.distinct(Transaction.user_id)).where(
            Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
            Transaction.is_completed.is_(True),
            Transaction.created_at >= prior_start_utc,
            Transaction.created_at < month_start_utc,
        )
    )
    prior_ids: set[int] = {row[0] for row in prior_result.all()}

    if not prior_ids:
        return 0

    # Users who paid this month
    current_result = await session.execute(
        select(func.distinct(Transaction.user_id)).where(
            Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
        )
    )
    current_ids: set[int] = {row[0] for row in current_result.all()}

    # Users with active subscription at end of today
    today_end_utc = datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)
    active_result = await session.execute(
        select(func.distinct(Subscription.user_id)).where(
            Subscription.is_trial.is_(False),
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.end_date > today_end_utc,
        )
    )
    active_ids: set[int] = {row[0] for row in active_result.all()}

    churned = prior_ids - current_ids - active_ids
    return len(churned)


async def _sum_referral_earnings(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> int:
    """Sum of referral commissions (kopeks) credited to referrers this month."""
    result = await session.execute(
        select(
            func.coalesce(func.sum(ReferralEarning.amount_kopeks), 0)
        ).where(
            ReferralEarning.created_at >= month_start_utc,
            ReferralEarning.created_at < day_end_utc,
        )
    )
    return int(result.scalar() or 0)


async def _sum_balance_credited(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> int:
    """
    Balance credits issued this month (kopeks).
    = REFERRAL_REWARD transactions (balance bonuses to referrers, poll rewards etc.)
    These are NOT cash outflows — they are internal liability credits.
    Displayed in Метрики row 11 as informational only.
    """
    result = await session.execute(
        select(
            func.coalesce(func.sum(func.abs(Transaction.amount_kopeks)), 0)
        ).where(
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
            Transaction.type.in_([
                TransactionType.REFERRAL_REWARD.value,
                TransactionType.POLL_REWARD.value,
            ]),
        )
    )
    return int(result.scalar() or 0)


async def _sum_balance_redeemed(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> int:
    """
    Balance redeemed for subscriptions this month (kopeks).
    = SUBSCRIPTION_PAYMENT with payment_method='balance'.
    Actual cash foregone by the platform (balance was previously credited from real revenue).
    """
    result = await session.execute(
        select(
            func.coalesce(func.sum(func.abs(Transaction.amount_kopeks)), 0)
        ).where(
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
            Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
            Transaction.payment_method == "balance",
        )
    )
    return int(result.scalar() or 0)


async def _count_new_referred_paying(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> tuple[int, int]:
    """
    Returns (new_referred_paying, total_new_paying_with_referrers) for k-factor.

    k-factor = new_paying_via_referral / paying_users_who_referred_someone
    """
    from sqlalchemy.sql import false

    # New non-trial subscriptions this month joined with user referral info
    result = await session.execute(
        select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.created_at >= month_start_utc,
            Subscription.created_at < day_end_utc,
            Subscription.is_trial == false(),
            Subscription.user_id.in_(
                select(User.id).where(User.referred_by_id.isnot(None))
            ),
        )
    )
    new_referred = int(result.scalar() or 0)

    # Paying users this month who referred someone (have a referral)
    result2 = await session.execute(
        select(func.count(func.distinct(User.id))).where(
            User.id.in_(
                select(func.distinct(Transaction.user_id)).where(
                    Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
                    Transaction.is_completed.is_(True),
                    Transaction.created_at >= month_start_utc,
                    Transaction.created_at < day_end_utc,
                )
            ),
            User.referred_by_id.isnot(None),
        )
    )
    total_paying_with_referrer = int(result2.scalar() or 0)

    return new_referred, total_paying_with_referrer


async def _revenue_kopeks(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> int:
    """
    Total revenue (kopeks) for the month.

    Revenue = SUBSCRIPTION_PAYMENT(real methods) + DEPOSIT(real methods).
    No double-counting because:
      - balance top-up flow: DEPOSIT(real) + SUBSCRIPTION_PAYMENT(balance)
        → only DEPOSIT counted
      - direct sub purchase (landing): SUBSCRIPTION_PAYMENT(real)
        → only SUBSCRIPTION_PAYMENT counted
    """
    result = await session.execute(
        select(
            func.coalesce(func.sum(func.abs(Transaction.amount_kopeks)), 0)
        ).where(
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
            Transaction.type.in_([
                TransactionType.SUBSCRIPTION_PAYMENT.value,
                TransactionType.DEPOSIT.value,
            ]),
            Transaction.payment_method.in_(list(_REAL_METHODS)),
        )
    )
    return int(result.scalar() or 0)


# ---------------------------------------------------------------------------
# Per-transaction row enrichment
# ---------------------------------------------------------------------------

def _best_subscription(
    txn: Transaction,
    subs_by_user: dict[int, list[Subscription]],
) -> Optional[Subscription]:
    """
    Find the subscription most likely tied to this transaction.

    Since there is no FK between Transaction and Subscription, we match by
    user_id and pick the subscription whose created_at is closest to the
    transaction timestamp within a 7-day window.
    Falls back to the most recent subscription for the user if none found in window.
    """
    subs = subs_by_user.get(txn.user_id, [])
    if not subs:
        return None
    txn_time = txn.created_at
    if txn_time is None:
        return subs[-1]

    best: Optional[Subscription] = None
    best_delta = timedelta(days=9999)
    for sub in subs:
        if sub.created_at is None:
            continue
        delta = abs(sub.created_at - txn_time)
        if delta < best_delta and delta <= timedelta(days=7):
            best_delta = delta
            best = sub

    return best if best is not None else subs[-1]


def _period_months(sub: Optional[Subscription]) -> Optional[float]:
    """
    Derive subscription period in months from start/end dates.
    Returns None if unavailable or zero.
    """
    if sub is None or sub.start_date is None or sub.end_date is None:
        return None
    days = (sub.end_date - sub.start_date).days
    if days <= 0:
        return None
    return _r2(days / 30.0)


def _build_transaction_row(
    txn: Transaction,
    subs_by_user: dict[int, list[Subscription]],
    converted_user_ids: set[int],
) -> list[Any]:
    """
    Build one row for the "Транзакции" sheet (columns A–N).

    All rows produced here are type "Доход".
    "Расход" rows are not produced because the actual DB has no clean mapping to
    the spec's 'balance_payment DEBIT' or 'promo discount' event types —
    those concepts do not exist as discrete transaction records in this schema.
    """
    user: Optional[User] = txn.user

    # A: Дата
    col_a = txn.created_at.strftime("%d.%m.%Y") if txn.created_at else ""

    # B: Тип
    col_b = "Доход"

    # E: Метод
    pm = txn.payment_method
    col_e = _detect_method(pm)

    # Amount
    amount_kopeks_abs = abs(txn.amount_kopeks or 0)
    amount_rub = _kopeks_rub(amount_kopeks_abs)

    is_stars = pm == "telegram_stars"
    is_balance = pm == "balance"

    # F: Сумма ₽ — empty for Stars and Balance rows; filled for RUB
    col_f: Any = "" if (is_stars or is_balance) else amount_rub

    # G: Stars — stars_count is NOT stored as a separate field in this DB.
    # It was encoded in the description string at payment time, but parsing
    # that text is fragile. Per spec: empty string when not available.
    col_g: Any = ""

    # H: ₽ итого — always filled.
    # For Stars: amount_kopeks already stores the ruble-equivalent at payment time
    # (converted by the Stars payment service, not by us).
    col_h: Any = amount_rub

    # C/D: Category / Subcategory
    txn_type = txn.type
    if is_balance and txn_type == TransactionType.SUBSCRIPTION_PAYMENT.value:
        col_c = "Подписка — балансом"
        col_d = "Подписка"
    elif txn_type == TransactionType.SUBSCRIPTION_PAYMENT.value:
        is_new = user is not None and user.id in converted_user_ids
        col_c = "Подписка — новая" if is_new else "Подписка — продление"
        col_d = "Подписка"
    elif txn_type == TransactionType.DEPOSIT.value:
        col_c = "Пополнение баланса"
        col_d = "Депозит"
    else:
        col_c = txn_type or ""
        col_d = ""

    # Subscription enrichment (only meaningful for SUBSCRIPTION_PAYMENT)
    sub: Optional[Subscription] = None
    if txn_type == TransactionType.SUBSCRIPTION_PAYMENT.value:
        sub = _best_subscription(txn, subs_by_user)

    period_m = _period_months(sub)
    tariff_name = (sub.tariff.name if sub and sub.tariff else "") if sub else ""

    # I: Период мес.
    col_i: Any = _r2(period_m) if period_m is not None else ""

    # J: MRR вклад = H / I
    col_j: Any = ""
    if period_m and period_m > 0 and col_h:
        col_j = _r2(col_h / period_m)

    # K: User ID (prefer telegram_id, fall back to internal id)
    if user:
        col_k = str(user.telegram_id or user.id)
    else:
        col_k = str(txn.user_id)

    # L: Тариф
    col_l = tariff_name

    # M: Реферал — user.referred_by_id is the referral FK in this schema
    col_m = "Да" if (user and user.referred_by_id is not None) else "Нет"

    # N: Комментарий
    col_n = txn.description or ""

    return [
        col_a, col_b, col_c, col_d, col_e,
        col_f, col_g, col_h, col_i, col_j,
        col_k, col_l, col_m, col_n,
    ]


# ---------------------------------------------------------------------------
# Monthly aggregate row builder
# ---------------------------------------------------------------------------

def _build_monthly_row(
    current_month: str,
    revenue_kopeks: int,
    new_paying: int,
    churned: int,
    prev_active: int,
    mrr_kopeks: float,
    referral_cost_kopeks: int,
) -> list[Any]:
    """
    Build the "По месяцам" row (columns A–N).

    Columns without a clean data source are written as "" per spec.
    - Расходы: no cash-expense events exist in this DB schema → ""
    - Инфраструктура: managed manually in the Инфраструктура sheet → ""
    - Маркетинг реклама: not tracked in DB → ""
    - Прочее: not tracked → ""
    """
    revenue_rub = _r2(revenue_kopeks / 100.0)
    expenses_rub = ""       # no cash expense events in schema
    profit_rub = revenue_rub  # Profit = Revenue when Expenses unknown
    margin_pct = ""         # can't compute without expenses

    churn_pct: Any = ""
    if prev_active > 0:
        churn_pct = _r1(churned / prev_active * 100)

    mrr_rub = _r2(mrr_kopeks / 100.0)
    infra_rub = ""          # from Инфраструктура sheet (owner-managed)
    ref_discount_rub = _r2(referral_cost_kopeks / 100.0)
    promo_rub = ""          # promo discounts not tracked as transactions
    advert_rub = ""         # advertising spend not in DB
    other_rub = ""

    return [
        current_month,   # A: Месяц
        revenue_rub,     # B: Выручка ₽
        expenses_rub,    # C: Расходы ₽
        profit_rub,      # D: Прибыль ₽
        margin_pct,      # E: Маржа %
        new_paying,      # F: Новых платящих
        churned,         # G: Отвалилось
        churn_pct,       # H: Churn %
        mrr_rub,         # I: MRR
        infra_rub,       # J: Инфраструктура ₽
        ref_discount_rub,# K: Маркетинг — реф. скидка факт ₽
        promo_rub,       # L: Маркетинг — промокоды ₽
        advert_rub,      # M: Маркетинг — реклама ₽
        other_rub,       # N: Прочее ₽
    ]


# ---------------------------------------------------------------------------
# Metrics rows builder
# ---------------------------------------------------------------------------

def _build_metrics_rows(
    mrr_rub: float,
    active_paying: int,
    revenue_rub: float,
    churned: int,
    prev_active: int,
    referral_cost_kopeks: int,
    new_paying: int,
    new_referred: int,
    paying_with_referrer: int,
    balance_credited_kopeks: int,
    balance_redeemed_kopeks: int,
) -> list[list[Any]]:
    """
    Build 12 rows for the "Метрики" sheet (columns A–C).
    Column C (Норма) is always "" — the target values are set manually by the owner.

    Order must match spec exactly (rows 1-12).
    """
    arpu: Any = ""
    if active_paying > 0:
        arpu = _r2(revenue_rub / active_paying)

    churn_rate_pct: Any = ""
    churn_rate_decimal: Optional[float] = None
    if prev_active > 0:
        churn_rate_decimal = churned / prev_active
        churn_rate_pct = _r1(churn_rate_decimal * 100)

    ltv: Any = ""
    if churn_rate_decimal and churn_rate_decimal > 0 and arpu != "":
        ltv = _r2(arpu / churn_rate_decimal)

    cac_ref: Any = ""
    if new_paying > 0:
        cac_ref = _r2(referral_cost_kopeks / 100.0 / new_paying)

    ltv_cac: Any = ""
    if ltv != "" and cac_ref != "" and cac_ref > 0:
        ltv_cac = _r2(ltv / cac_ref)

    margin_pct: Any = ""
    # Margin can't be computed accurately without expense data.
    # Approximate: balance redeemed is the only measurable cost.
    if revenue_rub > 0:
        cost_rub = _r2(balance_redeemed_kopeks / 100.0)
        margin_pct = _r1((revenue_rub - cost_rub) / revenue_rub * 100)

    k_factor: Any = ""
    if paying_with_referrer > 0:
        k_factor = _r2(new_referred / paying_with_referrer)

    balance_credited_rub = _r2(balance_credited_kopeks / 100.0)
    balance_redeemed_rub = _r2(balance_redeemed_kopeks / 100.0)

    # 12 rows, exact order from spec
    return [
        ["MRR",                      _r2(mrr_rub),        ""],  # 1
        ["Платящих (active)",         active_paying,       ""],  # 2
        ["ARPU",                      arpu,                ""],  # 3
        ["Churn %",                   churn_rate_pct,      ""],  # 4
        ["LTV",                       ltv,                 ""],  # 5
        ["CAC — рефералка",           cac_ref,             ""],  # 6
        ["LTV / CAC",                 ltv_cac,             ""],  # 7
        ["Маржа %",                   margin_pct,          ""],  # 8
        ["k-фактор",                  k_factor,            ""],  # 9
        ["Новых за месяц",            new_paying,          ""],  # 10
        ["Начислено на баланс ₽",     balance_credited_rub,""],  # 11
        ["Списано с баланса ₽",       balance_redeemed_rub,""],  # 12
    ]


# ---------------------------------------------------------------------------
# MRR computation from transaction rows
# ---------------------------------------------------------------------------

def _compute_mrr_kopeks(
    txns: list[Transaction],
    subs_by_user: dict[int, list[Subscription]],
) -> float:
    """
    Sum MRR contributions for all SUBSCRIPTION_PAYMENT transactions.
    MRR_contribution = abs(amount_kopeks) / period_months.
    Transactions without a determinable period are excluded.
    """
    total = 0.0
    for txn in txns:
        if txn.type != TransactionType.SUBSCRIPTION_PAYMENT.value:
            continue
        sub = _best_subscription(txn, subs_by_user)
        pm = _period_months(sub)
        if pm and pm > 0:
            total += abs(txn.amount_kopeks or 0) / pm
    return total


# ---------------------------------------------------------------------------
# Google Sheets write functions (synchronous, run in executor)
# ---------------------------------------------------------------------------

def _write_to_sheets(
    transactions_rows: list[list[Any]],
    monthly_row: list[Any],
    metrics_rows: list[list[Any]],
    current_month: str,
) -> None:
    """
    Perform all Google Sheets writes synchronously.
    Called via asyncio.to_thread to avoid blocking the event loop.

    Strategy per sheet:
    - Транзакции: full overwrite rows 2+
    - По месяцам:  upsert on column A value == current_month
    - Метрики:     full overwrite rows 2+
    - Инфраструктура: NOT touched

    gspread is imported lazily here so the bot can start even if the library
    is not yet installed (uv.lock not regenerated).
    """
    import gspread  # noqa: PLC0415 — lazy import intentional

    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_JSON_PATH)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    # ---- Транзакции ----
    ws_txn = spreadsheet.worksheet(SHEET_TRANSACTIONS)
    ws_txn.batch_clear(["A2:N1000"])
    if transactions_rows:
        ws_txn.append_rows(transactions_rows, value_input_option="USER_ENTERED")

    # ---- Метрики ----
    ws_met = spreadsheet.worksheet(SHEET_METRICS)
    ws_met.batch_clear(["A2:C1000"])
    if metrics_rows:
        ws_met.append_rows(metrics_rows, value_input_option="USER_ENTERED")

    # ---- По месяцам (upsert) ----
    ws_mon = spreadsheet.worksheet(SHEET_BY_MONTHS)
    col_a = ws_mon.col_values(1)  # 1-based column index
    if current_month in col_a:
        row_index = col_a.index(current_month) + 1  # convert to 1-based row number
        ws_mon.update(f"A{row_index}:N{row_index}", [monthly_row])
    else:
        ws_mon.append_rows([monthly_row], value_input_option="USER_ENTERED")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_daily_sync(db_session: AsyncSession) -> None:
    """
    Collect financial data for the current calendar month and write it to
    the Google Sheets spreadsheet configured via environment variables.

    Steps (per spec):
    1. Compute today / current_month
    2. Collect data for month start → today inclusive
    3. Write "Транзакции" — full overwrite from row 2
    4. Write "По месяцам" — upsert on current_month
    5. Write "Метрики" — full overwrite from row 2
    6. "Инфраструктура" — not touched
    """
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID environment variable is not set")
    if not GOOGLE_CREDENTIALS_JSON_PATH:
        raise ValueError("GOOGLE_CREDENTIALS_JSON_PATH environment variable is not set")

    today = date.today()
    current_month = today.strftime("%Y-%m")
    month_start_utc, day_end_utc = _month_bounds_utc(today)

    logger.info(
        "Начало синхронизации Google Sheets",
        month=current_month,
        month_start=month_start_utc.isoformat(),
        day_end=day_end_utc.isoformat(),
    )

    # --- Fetch data ---
    txns = await _fetch_transactions(db_session, month_start_utc, day_end_utc)
    user_ids: set[int] = {t.user_id for t in txns}

    subs_by_user = await _fetch_subscriptions_for_users(db_session, user_ids)
    converted_user_ids = await _fetch_converted_user_ids(
        db_session, user_ids, month_start_utc, day_end_utc
    )
    active_paying = await _count_active_paying(db_session)
    new_paying = await _count_new_paying(db_session, month_start_utc, day_end_utc)
    churned = await _count_churned(db_session, month_start_utc, day_end_utc, today)

    # Previous month's active paying (for churn %)
    prev_month_start = month_start_utc - timedelta(days=1)  # last day of prev month
    prev_month_start_utc = datetime(
        prev_month_start.year, prev_month_start.month, 1, tzinfo=UTC
    )
    # Approximation: users with active sub at start of current month =
    # users who had a SUBSCRIPTION_PAYMENT in the prior 3 months
    prior_result = await db_session.execute(
        select(func.count(func.distinct(Transaction.user_id))).where(
            Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc - timedelta(days=91),
            Transaction.created_at < month_start_utc,
        )
    )
    prev_active = int(prior_result.scalar() or 0)

    referral_cost_kopeks = await _sum_referral_earnings(
        db_session, month_start_utc, day_end_utc
    )
    balance_credited_kopeks = await _sum_balance_credited(
        db_session, month_start_utc, day_end_utc
    )
    balance_redeemed_kopeks = await _sum_balance_redeemed(
        db_session, month_start_utc, day_end_utc
    )
    revenue_kopeks = await _revenue_kopeks(db_session, month_start_utc, day_end_utc)
    new_referred, paying_with_referrer = await _count_new_referred_paying(
        db_session, month_start_utc, day_end_utc
    )

    # --- Build rows ---
    transactions_rows = [
        _build_transaction_row(txn, subs_by_user, converted_user_ids)
        for txn in txns
    ]

    mrr_kopeks = _compute_mrr_kopeks(txns, subs_by_user)
    revenue_rub = _r2(revenue_kopeks / 100.0)

    monthly_row = _build_monthly_row(
        current_month=current_month,
        revenue_kopeks=revenue_kopeks,
        new_paying=new_paying,
        churned=churned,
        prev_active=prev_active,
        mrr_kopeks=mrr_kopeks,
        referral_cost_kopeks=referral_cost_kopeks,
    )

    metrics_rows = _build_metrics_rows(
        mrr_rub=mrr_kopeks / 100.0,
        active_paying=active_paying,
        revenue_rub=revenue_rub,
        churned=churned,
        prev_active=prev_active,
        referral_cost_kopeks=referral_cost_kopeks,
        new_paying=new_paying,
        new_referred=new_referred,
        paying_with_referrer=paying_with_referrer,
        balance_credited_kopeks=balance_credited_kopeks,
        balance_redeemed_kopeks=balance_redeemed_kopeks,
    )

    # --- Write to sheets (sync I/O → thread) ---
    try:
        await asyncio.to_thread(
            _write_to_sheets,
            transactions_rows,
            monthly_row,
            metrics_rows,
            current_month,
        )
    except Exception as exc:
        logger.error("Ошибка записи в Google Sheets", exc_info=exc)
        raise

    logger.info(
        "Синхронизация Google Sheets завершена",
        month=current_month,
        transactions_written=len(transactions_rows),
    )
