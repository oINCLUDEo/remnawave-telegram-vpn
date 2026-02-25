"""Tariff routes for the Mobile API v1.

GET /mobile/v1/tariffs
    Public endpoint — no authentication required.
    When called anonymously, returns tariffs with default promo-group discounts.
    When called with a valid Bearer token, returns tariffs with the
    authenticated user's promo-group discounts (and marks the current tariff).
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_optional_cabinet_user
from app.config import settings
from app.database.crud.promo_group import get_default_promo_group
from app.database.crud.subscription import get_subscription_by_user_id
from app.database.crud.tariff import get_tariffs_for_user
from app.database.models import PromoGroup, User
from app.utils.pricing_utils import format_period_description

from ..schemas import MobileTariff, MobileTariffPeriod, MobileTariffsResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Mobile — Tariffs'])


def _build_period(
    period_days: int,
    price_kopeks: int,
    promo_group: PromoGroup | None,
    language: str,
) -> MobileTariffPeriod:
    """Build a single period entry with optional promo-group discount applied."""
    months = max(1, period_days // 30)
    base_price = price_kopeks

    discount_percent = 0
    final_price = base_price
    if promo_group:
        discount_percent = promo_group.get_discount_percent('period', period_days)
        if discount_percent > 0:
            discount_amount = base_price * discount_percent // 100
            final_price = base_price - discount_amount

    per_month = final_price // months if months > 0 else final_price

    original_price_label: str | None = None
    if discount_percent > 0:
        original_price_label = settings.format_price(base_price)

    return MobileTariffPeriod(
        days=period_days,
        months=months,
        label=format_period_description(period_days, language),
        price_label=settings.format_price(final_price),
        price_per_month_label=settings.format_price(per_month),
        discount_percent=discount_percent,
        original_price_label=original_price_label,
    )


def _build_tariff(
    tariff: Any,
    current_tariff_id: int | None,
    promo_group: PromoGroup | None,
    language: str,
) -> MobileTariff:
    """Convert a DB Tariff model into a MobileTariff schema."""
    traffic_label = (
        '♾️ Безлимит' if tariff.traffic_limit_gb == 0 else f'{tariff.traffic_limit_gb} ГБ'
    )

    allowed_periods: set[int] = set(settings.get_available_subscription_periods())

    periods: list[MobileTariffPeriod] = []
    if tariff.period_prices:
        for period_str, price_kopeks in sorted(
            tariff.period_prices.items(), key=lambda x: int(x[0])
        ):
            period_days = int(period_str)
            if int(price_kopeks) < 0:
                continue  # negative price means period is disabled
            if allowed_periods and period_days not in allowed_periods:
                continue  # period not enabled in AVAILABLE_SUBSCRIPTION_PERIODS
            periods.append(
                _build_period(period_days, int(price_kopeks), promo_group, language)
            )

    return MobileTariff(
        id=tariff.id,
        name=tariff.name,
        description=tariff.description,
        traffic_limit_gb=tariff.traffic_limit_gb,
        traffic_limit_label=traffic_label,
        device_limit=tariff.device_limit,
        periods=periods,
        is_current=current_tariff_id == tariff.id if current_tariff_id else False,
    )


@router.get('/tariffs', response_model=MobileTariffsResponse)
async def get_tariffs(
    user: User | None = Depends(get_optional_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> MobileTariffsResponse:
    """
    Return all active tariff plans.

    Authentication is **optional**.  When called anonymously the default
    promo group's discounts are applied so the prices shown to new users
    match what they will actually pay.  When called with a valid Bearer token
    the authenticated user's promo group discounts are used instead.
    """
    try:
        promo_group: PromoGroup | None = None
        promo_group_id: int | None = None
        current_tariff_id: int | None = None
        language = 'ru'

        if user is not None:
            # Authenticated request — use the user's actual promo group.
            pg = (
                user.get_primary_promo_group()
                if hasattr(user, 'get_primary_promo_group')
                else None
            )
            if pg is None:
                pg = getattr(user, 'promo_group', None)
            promo_group = pg
            promo_group_id = pg.id if pg else None
            language = getattr(user, 'language', 'ru') or 'ru'
            subscription = await get_subscription_by_user_id(db, user.id)
            current_tariff_id = subscription.tariff_id if subscription else None
        else:
            # Anonymous request — apply default promo group so prices match
            # what a freshly-registered user would see.
            default_group = await get_default_promo_group(db)
            if default_group is not None:
                promo_group = default_group
                promo_group_id = default_group.id

        tariffs = await get_tariffs_for_user(db, promo_group_id)

        mobile_tariffs = [
            _build_tariff(t, current_tariff_id, promo_group, language)
            for t in tariffs
            if t.period_prices  # skip tariffs with no purchasable periods
        ]

        return MobileTariffsResponse(
            tariffs=mobile_tariffs,
            current_tariff_id=current_tariff_id,
        )

    except Exception as exc:
        logger.error('mobile_api: failed to build tariffs response', error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to load tariffs',
        ) from exc
