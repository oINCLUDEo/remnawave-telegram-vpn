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
import re
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
    Tariff,
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
SHEET_BY_TARIFFS = "По тарифам"
SHEET_ANALYTICS = "Аналитика"

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


def _extract_period_months(description: Optional[str]) -> Optional[float]:
    """
    Extract period in months from transaction description.
    Looks for the pattern 'на N дней' which is always present in subscription
    descriptions like 'Покупка тарифа X на 30 дней'.
    This is more reliable than (end_date - start_date) because renewals extend
    end_date cumulatively, making the date-diff much larger than the actual
    paid period.
    """
    if not description:
        return None
    match = re.search(r'на\s+(\d+)\s+дней', description)
    if match:
        days = int(match.group(1))
        if days > 0:
            return _r2(days / 30.0)
    return None


def _extract_stars_count(description: Optional[str]) -> Optional[int]:
    """
    Extract Telegram Stars count from deposit description.
    Matches patterns like 'Пополнение через Telegram Stars (8 ⭐)'.
    """
    if not description:
        return None
    match = re.search(r'\((\d+)\s*[⭐★]\)', description)
    if match:
        return int(match.group(1))
    return None


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


def _month_range_utc(ref_date: date, today: date) -> tuple[datetime, datetime]:
    """
    Return (month_start_utc, exclusive_end_utc) for any target month.

    For the current month: end = start of tomorrow (data up to today inclusive).
    For a past month:      end = first day of the next month (full calendar month).
    """
    month_start = datetime(ref_date.year, ref_date.month, 1, tzinfo=UTC)

    if ref_date.year == today.year and ref_date.month == today.month:
        # Current month — up to end of today
        day_end = datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)
    else:
        # Past month — full month
        if ref_date.month == 12:
            day_end = datetime(ref_date.year + 1, 1, 1, tzinfo=UTC)
        else:
            day_end = datetime(ref_date.year, ref_date.month + 1, 1, tzinfo=UTC)

    return month_start, day_end


def _prev_month_date(today: date) -> date:
    """Return the first day of the previous calendar month."""
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


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
) -> tuple[int, int]:
    """
    Cohort-based churn.  Returns (churned_count, active_at_start_count).

    Definition:
      active_at_start = non-trial subscriptions where
          end_date >= month_start   (was still running on day 1 of month M)
          AND created_at < month_start  (existed before month M)

      churned = active_at_start users who have NO non-trial subscription
                with end_date >= day_end_utc
                (their subscription expired during M and was not renewed)

      churn_pct = churned / active_at_start * 100

    Why this is correct vs the previous transaction-based approach:
      The old code used "users who ever paid before M" as the cohort.
      That included users who paid 6 months ago and whose subscription
      expired long before M — they were never at risk of churning in M.
      This inflated the churn count (52 vs real 18 for May 2026).

    Verified formula: start(170) + new(55) - churned(18) = end(207) ✓
    """
    # Users with an active non-trial subscription at the START of month M
    start_result = await session.execute(
        select(func.distinct(Subscription.user_id)).where(
            Subscription.is_trial.is_(False),
            Subscription.end_date >= month_start_utc,
            Subscription.created_at < month_start_utc,
        )
    )
    active_at_start_ids: set[int] = {row[0] for row in start_result.all()}

    if not active_at_start_ids:
        return 0, 0

    # From that cohort, who still has a subscription running through month end
    # (end_date >= day_end_utc → renewed or multi-month plan covers full month)
    still_active_result = await session.execute(
        select(func.distinct(Subscription.user_id)).where(
            Subscription.user_id.in_(list(active_at_start_ids)),
            Subscription.is_trial.is_(False),
            Subscription.end_date >= day_end_utc,
        )
    )
    still_active_ids: set[int] = {row[0] for row in still_active_result.all()}

    churned = active_at_start_ids - still_active_ids
    return len(churned), len(active_at_start_ids)


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


async def _count_referral_stats(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> tuple[int, int]:
    """
    Returns (first_deposit_referred, total_new_paying_referred) for k-factor.

    first_deposit_referred — users whose FIRST EVER real deposit is in this month
    AND referred_by_id IS NOT NULL.  Used for correct CAC calculation:
      CAC_referral = referral_reward_credits_this_month / first_deposit_referred

    total_new_paying_referred — new paying users this month who were referred.
    Used for k-factor numerator.
    """
    # Users who deposited BEFORE this month (exclude from "first deposit" count)
    deposited_before = select(func.distinct(Transaction.user_id)).where(
        Transaction.type.in_([
            TransactionType.DEPOSIT.value,
            TransactionType.SUBSCRIPTION_PAYMENT.value,
        ]),
        Transaction.is_completed.is_(True),
        Transaction.payment_method.in_(list(_REAL_METHODS)),
        Transaction.created_at < month_start_utc,
    )

    # First-time depositors this month who were referred
    first_result = await session.execute(
        select(func.count(func.distinct(Transaction.user_id))).where(
            Transaction.type.in_([
                TransactionType.DEPOSIT.value,
                TransactionType.SUBSCRIPTION_PAYMENT.value,
            ]),
            Transaction.is_completed.is_(True),
            Transaction.payment_method.in_(list(_REAL_METHODS)),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
            Transaction.user_id.not_in(deposited_before),
            Transaction.user_id.in_(
                select(User.id).where(User.referred_by_id.isnot(None))
            ),
        )
    )
    first_deposit_referred = int(first_result.scalar() or 0)

    # All new paying users this month who were referred (for k-factor)
    from sqlalchemy.sql import false as sql_false

    k_result = await session.execute(
        select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.created_at >= month_start_utc,
            Subscription.created_at < day_end_utc,
            Subscription.is_trial == sql_false(),
            Subscription.user_id.in_(
                select(User.id).where(User.referred_by_id.isnot(None))
            ),
        )
    )
    total_new_paying_referred = int(k_result.scalar() or 0)

    # Paying users this month who have referred someone else (k-factor denominator)
    k_denom_result = await session.execute(
        select(func.count(func.distinct(User.id))).where(
            User.id.in_(
                select(func.distinct(Transaction.user_id)).where(
                    Transaction.type.in_([
                        TransactionType.DEPOSIT.value,
                        TransactionType.SUBSCRIPTION_PAYMENT.value,
                    ]),
                    Transaction.is_completed.is_(True),
                    Transaction.payment_method.in_(list(_REAL_METHODS)),
                    Transaction.created_at >= month_start_utc,
                    Transaction.created_at < day_end_utc,
                )
            ),
            User.referred_by_id.isnot(None),
        )
    )
    paying_with_referrer = int(k_denom_result.scalar() or 0)

    return first_deposit_referred, total_new_paying_referred, paying_with_referrer


async def _sum_manual_expenses(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> dict[str, float]:
    """
    Sum manual_expenses rows for the month, grouped by category.
    Returns {'infrastructure': ₽, 'marketing_ads': ₽, 'other': ₽}.
    Returns zeros gracefully if the table doesn't exist yet.
    """
    from sqlalchemy import text

    month_start_date = month_start_utc.date()
    month_end_date = (day_end_utc - timedelta(seconds=1)).date()
    result = {"infrastructure": 0.0, "marketing_ads": 0.0, "other": 0.0}

    try:
        rows = await session.execute(
            text(
                "SELECT category, SUM(amount_rub) FROM manual_expenses "
                "WHERE expense_date >= :start AND expense_date <= :end "
                "GROUP BY category"
            ),
            {"start": month_start_date, "end": month_end_date},
        )
        for category, total in rows.all():
            if category in result:
                result[category] = round(float(total or 0), 2)
    except Exception:
        # Table not created yet — return zeros silently
        pass

    return result


async def _fetch_tariff_stats(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
) -> list[dict]:
    """
    Per-tariff breakdown for the current month.
    Returns list of dicts with tariff analytics.
    """
    from sqlalchemy.sql import false as sql_false

    # Active subscriptions right now, grouped by tariff
    active_result = await session.execute(
        select(
            Tariff.name,
            func.count(func.distinct(Subscription.user_id)).label("active_count"),
        )
        .join(Tariff, Subscription.tariff_id == Tariff.id)
        .where(
            Subscription.is_trial == sql_false(),
            Subscription.end_date >= datetime.now(UTC),
        )
        .group_by(Tariff.name)
        .order_by(func.count(func.distinct(Subscription.user_id)).desc())
    )
    active_by_tariff = {row.name: row.active_count for row in active_result.all()}

    # New subscriptions this month by tariff
    new_result = await session.execute(
        select(
            Tariff.name,
            func.count(Subscription.id).label("new_count"),
        )
        .join(Tariff, Subscription.tariff_id == Tariff.id)
        .where(
            Subscription.is_trial == sql_false(),
            Subscription.created_at >= month_start_utc,
            Subscription.created_at < day_end_utc,
        )
        .group_by(Tariff.name)
    )
    new_by_tariff = {row.name: row.new_count for row in new_result.all()}

    # Revenue this month by tariff (SUBSCRIPTION_PAYMENT linked via description tariff name)
    # We match via subscriptions created in same window (same user_id proximity)
    rev_result = await session.execute(
        select(
            Tariff.name,
            func.coalesce(func.sum(func.abs(Transaction.amount_kopeks)), 0).label("rev"),
        )
        .join(Subscription, Transaction.user_id == Subscription.user_id)
        .join(Tariff, Subscription.tariff_id == Tariff.id)
        .where(
            Transaction.type == TransactionType.SUBSCRIPTION_PAYMENT.value,
            Transaction.is_completed.is_(True),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
            Subscription.is_trial == sql_false(),
        )
        .group_by(Tariff.name)
    )
    rev_by_tariff = {row.name: int(row.rev) for row in rev_result.all()}

    # Collect all tariff names
    all_names = set(active_by_tariff) | set(new_by_tariff) | set(rev_by_tariff)
    total_active = sum(active_by_tariff.values()) or 1

    rows = []
    for name in sorted(all_names):
        active = active_by_tariff.get(name, 0)
        new = new_by_tariff.get(name, 0)
        rev_kopeks = rev_by_tariff.get(name, 0)
        rev_rub = _r2(rev_kopeks / 100.0)
        share_pct = _r1(active / total_active * 100)
        rows.append({
            "name": name,
            "active": active,
            "new": new,
            "rev_rub": rev_rub,
            "share_pct": share_pct,
        })

    return sorted(rows, key=lambda x: x["active"], reverse=True)


async def _fetch_analytics_stats(
    session: AsyncSession,
    month_start_utc: datetime,
    day_end_utc: datetime,
    revenue_kopeks: int,
    active_at_start: int,
    churned: int,
    new_paying: int,
) -> dict:
    """
    Compute analytics metrics including month-over-month comparisons.
    Fetches previous month data for growth calculations.
    """
    from sqlalchemy.sql import false as sql_false

    # Active subscribers at END of this month
    active_at_end_result = await session.execute(
        select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.is_trial == sql_false(),
            Subscription.end_date >= day_end_utc,
        )
    )
    active_at_end = int(active_at_end_result.scalar() or 0)

    # Previous month bounds for comparison
    prev_end = month_start_utc
    if month_start_utc.month == 1:
        prev_start = datetime(month_start_utc.year - 1, 12, 1, tzinfo=UTC)
    else:
        prev_start = datetime(month_start_utc.year, month_start_utc.month - 1, 1, tzinfo=UTC)

    # Previous month revenue
    prev_rev_result = await session.execute(
        select(func.coalesce(func.sum(func.abs(Transaction.amount_kopeks)), 0)).where(
            Transaction.is_completed.is_(True),
            Transaction.created_at >= prev_start,
            Transaction.created_at < prev_end,
            Transaction.type.in_([
                TransactionType.DEPOSIT.value,
                TransactionType.SUBSCRIPTION_PAYMENT.value,
            ]),
            Transaction.payment_method.in_(list(_REAL_METHODS)),
        )
    )
    prev_rev_kopeks = int(prev_rev_result.scalar() or 0)

    # Previous month active at end
    prev_active_end_result = await session.execute(
        select(func.count(func.distinct(Subscription.user_id))).where(
            Subscription.is_trial == sql_false(),
            Subscription.end_date >= prev_end,
        )
    )
    prev_active_end = int(prev_active_end_result.scalar() or 0)

    # Growth %
    rev_growth_pct: Any = ""
    if prev_rev_kopeks > 0:
        rev_growth_pct = _r1((revenue_kopeks - prev_rev_kopeks) / prev_rev_kopeks * 100)

    user_growth_pct: Any = ""
    if prev_active_end > 0:
        user_growth_pct = _r1((active_at_end - prev_active_end) / prev_active_end * 100)

    # Retention = (active_at_start - churned) / active_at_start
    retention_pct: Any = ""
    if active_at_start > 0:
        retention_pct = _r1((active_at_start - churned) / active_at_start * 100)

    # ARPU new vs returning (all paying in month)
    all_paying_result = await session.execute(
        select(func.count(func.distinct(Transaction.user_id))).where(
            Transaction.type.in_([
                TransactionType.DEPOSIT.value,
                TransactionType.SUBSCRIPTION_PAYMENT.value,
            ]),
            Transaction.is_completed.is_(True),
            Transaction.payment_method.in_(list(_REAL_METHODS)),
            Transaction.created_at >= month_start_utc,
            Transaction.created_at < day_end_utc,
        )
    )
    all_paying = int(all_paying_result.scalar() or 1)
    arpu_all: Any = _r2(revenue_kopeks / 100.0 / all_paying) if all_paying > 0 else ""

    # LTV estimate: ARPU / monthly_churn_rate
    ltv_estimate: Any = ""
    if active_at_start > 0 and churned >= 0 and arpu_all != "":
        monthly_churn = churned / active_at_start
        if monthly_churn > 0:
            ltv_estimate = _r2(arpu_all / monthly_churn)

    # Conversion rate: trial → paid this month
    conv_result = await session.execute(
        select(func.count(SubscriptionConversion.id)).where(
            SubscriptionConversion.converted_at >= month_start_utc,
            SubscriptionConversion.converted_at < day_end_utc,
        )
    )
    conversions = int(conv_result.scalar() or 0)
    trial_result = await session.execute(
        select(func.count(Subscription.id)).where(
            Subscription.created_at >= month_start_utc,
            Subscription.created_at < day_end_utc,
            Subscription.is_trial.is_(True),
        )
    )
    new_trials = int(trial_result.scalar() or 0)
    conv_rate: Any = _r1(conversions / new_trials * 100) if new_trials > 0 else ""

    return {
        "active_at_end": active_at_end,
        "rev_growth_pct": rev_growth_pct,
        "user_growth_pct": user_growth_pct,
        "retention_pct": retention_pct,
        "arpu_all": arpu_all,
        "ltv_estimate": ltv_estimate,
        "conv_rate": conv_rate,
        "new_trials": new_trials,
    }


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

    # E: Метод
    pm = txn.payment_method
    col_e = _detect_method(pm)

    # Amount
    amount_kopeks_abs = abs(txn.amount_kopeks or 0)
    amount_rub = _kopeks_rub(amount_kopeks_abs)

    is_stars = pm == "telegram_stars"
    is_balance = pm == "balance"

    # B: Тип
    # Balance subscriptions are INTERNAL transfers (balance debit), not a new
    # cash inflow → show as "—", not "Доход". Real revenue is the DEPOSIT row
    # that funded the balance. This prevents double-counting in any manual sum.
    if is_balance and txn.type == TransactionType.SUBSCRIPTION_PAYMENT.value:
        col_b = "—"
    else:
        col_b = "Доход"

    # F: Сумма ₽ — empty for Stars and Balance rows; filled for RUB
    col_f: Any = "" if (is_stars or is_balance) else amount_rub

    # G: Stars count — extracted from description when available.
    # Example description: "Пополнение через Telegram Stars (8 ⭐)"
    stars_count = _extract_stars_count(txn.description) if is_stars else None
    col_g: Any = stars_count if stars_count is not None else ""

    # H: ₽ итого — always filled.
    # For Stars: amount_kopeks already stores the ruble-equivalent at payment time.
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

    # Period: prefer description-based extraction ("на 30 дней") as it reflects
    # the actual purchased period, not the cumulative subscription window.
    period_m = _extract_period_months(txn.description)
    if period_m is None and txn_type == TransactionType.SUBSCRIPTION_PAYMENT.value:
        period_m = _period_months(sub)  # fallback to date diff

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
    active_at_start: int,
    mrr_kopeks: float,
    referral_issued_kopeks: int,
    manual_expenses: dict[str, float],
) -> list[Any]:
    """
    Build the "По месяцам" row (columns A–N).

    expenses_rub = only hard cash outflows: infra + ads + other (manual_expenses).
    Referral balance issued is informational only → column K, NOT in expenses_rub.
    Reason: referral_earnings are liability credits; many are never spent.
    Including them in expenses overstates costs with money that may never flow out.
    """
    revenue_rub = _r2(revenue_kopeks / 100.0)

    infra_rub = _r2(manual_expenses.get("infrastructure", 0.0))
    ads_rub = _r2(manual_expenses.get("marketing_ads", 0.0))
    other_rub = _r2(manual_expenses.get("other", 0.0))

    # Expenses = only cash outflows recorded in manual_expenses
    expenses_rub = _r2(infra_rub + ads_rub + other_rub)
    profit_rub = _r2(revenue_rub - expenses_rub)
    margin_pct: Any = _r1(profit_rub / revenue_rub * 100) if revenue_rub > 0 else ""

    # Churn denominator = cohort size at start of month (from _count_churned)
    churn_pct: Any = _r1(churned / active_at_start * 100) if active_at_start > 0 else ""
    mrr_rub = _r2(mrr_kopeks / 100.0)

    # Column K: referral balance issued this month — informational, not in expenses
    ref_issued_rub = _r2(referral_issued_kopeks / 100.0)

    return [
        current_month,   # A: Месяц
        revenue_rub,     # B: Выручка ₽
        expenses_rub,    # C: Расходы ₽  (infra + ads + other only)
        profit_rub,      # D: Прибыль ₽
        margin_pct,      # E: Маржа %
        new_paying,      # F: Новых платящих
        churned,         # G: Отвалилось
        churn_pct,       # H: Churn %
        mrr_rub,         # I: MRR
        infra_rub,       # J: Инфраструктура ₽
        ref_issued_rub,  # K: Реф. баланс выдано ₽ (informational, not in C)
        "",              # L: Промокоды (not tracked)
        ads_rub,         # M: Реклама ₽
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
    active_at_start: int,
    referral_issued_kopeks: int,
    first_deposit_referred: int,
    new_paying: int,
    new_referred: int,
    paying_with_referrer: int,
    manual_expenses: dict[str, float],
) -> list[list[Any]]:
    """
    Build 12 rows for the "Метрики" sheet (columns A–C).
    Column C (Норма) is always "" — set manually by owner.

    Referral notes:
      Row 11 — "Начислено рефереррам ₽": referral balance ISSUED (liabilities accrued)
      Row 12 — "Использовано рефбаланса ₽": "" — balance is a shared pool
               (referral + deposits mixed), impossible to attribute cleanly.
    """
    arpu: Any = _r2(revenue_rub / active_paying) if active_paying > 0 else ""

    churn_rate_decimal: Optional[float] = None
    churn_rate_pct: Any = ""
    if active_at_start > 0:
        churn_rate_decimal = churned / active_at_start
        churn_rate_pct = _r1(churn_rate_decimal * 100)

    ltv: Any = ""
    if churn_rate_decimal and churn_rate_decimal > 0 and arpu != "":
        ltv = _r2(arpu / churn_rate_decimal)

    # CAC = referral rewards issued / first-time depositors via referral
    cac_ref: Any = ""
    if first_deposit_referred > 0:
        cac_ref = _r2(referral_issued_kopeks / 100.0 / first_deposit_referred)

    ltv_cac: Any = ""
    if ltv != "" and cac_ref != "" and cac_ref > 0:
        ltv_cac = _r2(ltv / cac_ref)

    # Margin = (revenue - cash expenses) / revenue
    # Cash expenses = manual_expenses only (no referral liabilities)
    cash_expenses_rub = sum(manual_expenses.values())
    margin_pct: Any = (
        _r1((revenue_rub - cash_expenses_rub) / revenue_rub * 100)
        if revenue_rub > 0 else ""
    )

    k_factor: Any = _r2(new_referred / paying_with_referrer) if paying_with_referrer > 0 else ""

    referral_issued_rub = _r2(referral_issued_kopeks / 100.0)

    # 12 rows, exact order from spec
    return [
        ["MRR",                        _r2(mrr_rub),         ""],  # 1
        ["Платящих (active)",           active_paying,        ""],  # 2
        ["ARPU",                        arpu,                 ""],  # 3
        ["Churn %",                     churn_rate_pct,       ""],  # 4
        ["LTV",                         ltv,                  ""],  # 5
        ["CAC — рефералка",             cac_ref,              ""],  # 6
        ["LTV / CAC",                   ltv_cac,              ""],  # 7
        ["Маржа %",                     margin_pct,           ""],  # 8
        ["k-фактор",                    k_factor,             ""],  # 9
        ["Новых за месяц",              new_paying,           ""],  # 10
        ["Начислено рефереррам ₽",      referral_issued_rub,  ""],  # 11
        ["Использовано рефбаланса ₽",   "",                   ""],  # 12 — shared pool, can't split
    ]


# ---------------------------------------------------------------------------
# New sheet row builders
# ---------------------------------------------------------------------------

TARIFFS_HEADER = [
    "Тариф", "Активных", "Новых за месяц", "Выручка ₽", "Доля %",
    "30-дн.", "60-дн.", "90-дн.+",
]

ANALYTICS_HEADER = [
    "Месяц", "Активных конец", "Рост выручки %", "Рост активных %",
    "Retention %", "ARPU ₽", "LTV прогноз ₽", "Конверсия trial→paid %",
    "Новых триалов", "Новых платящих",
]


def _build_tariff_rows(tariff_stats: list[dict]) -> list[list[Any]]:
    rows = []
    for t in tariff_stats:
        rows.append([
            t["name"],
            t["active"],
            t["new"],
            t["rev_rub"],
            t["share_pct"],
            "", "", "",  # 30/60/90 day breakdown — placeholder
        ])
    return rows


def _build_analytics_row(
    current_month: str,
    analytics: dict,
    new_paying: int,
) -> list[Any]:
    return [
        current_month,
        analytics["active_at_end"],
        analytics["rev_growth_pct"],
        analytics["user_growth_pct"],
        analytics["retention_pct"],
        analytics["arpu_all"],
        analytics["ltv_estimate"],
        analytics["conv_rate"],
        analytics["new_trials"],
        new_paying,
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

def _ensure_sheet(spreadsheet, name: str, headers: list[str]) -> Any:
    """Return worksheet by name, creating it with headers if it doesn't exist."""
    import gspread  # noqa: PLC0415

    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=500, cols=len(headers) + 2)
        ws.append_row(headers, value_input_option="USER_ENTERED")
        return ws


def _write_to_sheets(
    transactions_rows: list[list[Any]],
    monthly_row: list[Any],
    metrics_rows: list[list[Any]],
    tariff_rows: list[list[Any]],
    analytics_row: list[Any],
    current_month: str,
) -> None:
    """
    Perform all Google Sheets writes synchronously.
    Called via asyncio.to_thread to avoid blocking the event loop.

    Strategy:
    - Транзакции: full overwrite rows 2+
    - По месяцам: upsert on column A == current_month
    - Метрики:    full overwrite rows 2+
    - По тарифам: full overwrite rows 2+ (auto-created if missing)
    - Аналитика:  upsert on column A == current_month (auto-created if missing)
    - Инфраструктура: NOT touched (owner-managed)
    """
    import gspread  # noqa: PLC0415 — lazy import intentional
    from bot.export.sheets_format import apply_all_formatting  # noqa: PLC0415

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
    col_a = ws_mon.col_values(1)
    if current_month in col_a:
        row_index = col_a.index(current_month) + 1
        ws_mon.update(f"A{row_index}:N{row_index}", [monthly_row])
    else:
        ws_mon.append_rows([monthly_row], value_input_option="USER_ENTERED")

    # ---- По тарифам (full overwrite, auto-create) ----
    from bot.export.sheets_sync import TARIFFS_HEADER  # noqa: PLC0415
    ws_tar = _ensure_sheet(spreadsheet, SHEET_BY_TARIFFS, TARIFFS_HEADER)
    ws_tar.batch_clear(["A2:H500"])
    if tariff_rows:
        ws_tar.append_rows(tariff_rows, value_input_option="USER_ENTERED")

    # ---- Аналитика (upsert, auto-create) ----
    from bot.export.sheets_sync import ANALYTICS_HEADER  # noqa: PLC0415
    ws_ana = _ensure_sheet(spreadsheet, SHEET_ANALYTICS, ANALYTICS_HEADER)
    col_a_ana = ws_ana.col_values(1)
    if current_month in col_a_ana:
        row_idx = col_a_ana.index(current_month) + 1
        ws_ana.update(f"A{row_idx}:J{row_idx}", [analytics_row])
    else:
        ws_ana.append_rows([analytics_row], value_input_option="USER_ENTERED")

    # ---- Formatting + Charts (best-effort, non-blocking errors) ----
    try:
        existing = [ws.title for ws in spreadsheet.worksheets()]
        mon_rows = len(col_a) + 1
        row_counts = {
            "По месяцам": mon_rows,
            "По тарифам": len(tariff_rows) + 1,
            "Аналитика": len(col_a_ana) + 1,
        }
        apply_all_formatting(spreadsheet, existing, row_counts)
    except Exception:
        pass  # formatting failure must not abort the sync


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_daily_sync(
    db_session: AsyncSession,
    target_date: Optional[date] = None,
) -> None:
    """
    Collect financial data for the target month and write it to Google Sheets.

    target_date — any date within the desired month.
                  Defaults to today (= current month).
                  Pass the first day of a past month to back-fill it.

    Steps:
    1. Compute ref_date / current_month
    2. Collect data: current month → start..today; past month → full calendar month
    3. Write "Транзакции" — full overwrite from row 2
    4. Write "По месяцам" — upsert on month key
    5. Write "Метрики" — full overwrite from row 2
    6. "Инфраструктура" — not touched
    """
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID environment variable is not set")
    if not GOOGLE_CREDENTIALS_JSON_PATH:
        raise ValueError("GOOGLE_CREDENTIALS_JSON_PATH environment variable is not set")

    today = date.today()
    ref_date = target_date or today
    current_month = ref_date.strftime("%Y-%m")
    month_start_utc, day_end_utc = _month_range_utc(ref_date, today)

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
    # Returns (churned_count, active_at_start_count) — cohort-based
    churned, active_at_start = await _count_churned(db_session, month_start_utc, day_end_utc)

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
    first_deposit_referred, new_referred, paying_with_referrer = (
        await _count_referral_stats(db_session, month_start_utc, day_end_utc)
    )
    manual_expenses = await _sum_manual_expenses(
        db_session, month_start_utc, day_end_utc
    )
    tariff_stats = await _fetch_tariff_stats(
        db_session, month_start_utc, day_end_utc
    )
    analytics_stats = await _fetch_analytics_stats(
        db_session, month_start_utc, day_end_utc,
        revenue_kopeks, active_at_start, churned, new_paying,
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
        active_at_start=active_at_start,
        mrr_kopeks=mrr_kopeks,
        referral_issued_kopeks=referral_cost_kopeks,
        manual_expenses=manual_expenses,
    )

    metrics_rows = _build_metrics_rows(
        mrr_rub=mrr_kopeks / 100.0,
        active_paying=active_paying,
        revenue_rub=revenue_rub,
        churned=churned,
        active_at_start=active_at_start,
        referral_issued_kopeks=referral_cost_kopeks,
        first_deposit_referred=first_deposit_referred,
        new_paying=new_paying,
        new_referred=new_referred,
        paying_with_referrer=paying_with_referrer,
        manual_expenses=manual_expenses,
    )

    tariff_rows = _build_tariff_rows(tariff_stats)
    analytics_row = _build_analytics_row(current_month, analytics_stats, new_paying)

    # --- Write to sheets (sync I/O → thread) ---
    try:
        await asyncio.to_thread(
            _write_to_sheets,
            transactions_rows,
            monthly_row,
            metrics_rows,
            tariff_rows,
            analytics_row,
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
