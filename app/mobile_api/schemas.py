"""Pydantic schemas for the Mobile API v1.

These models define the exact JSON shape returned to the Flutter app.
They are intentionally simpler than the internal cabinet API — only fields
the mobile client actually needs are exposed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MobileTariffPeriod(BaseModel):
    """A single purchasable period (e.g. 1 month, 3 months) within a tariff."""

    model_config = ConfigDict(populate_by_name=True)

    days: int
    months: int
    label: str  # localised human-readable period, e.g. "1 месяц"
    price_label: str  # formatted final price, e.g. "299 ₽"
    price_per_month_label: str  # formatted per-month price, e.g. "299 ₽/мес"
    discount_percent: int  # 0 when no discount applies
    original_price_label: str | None = None  # only present when discount > 0


class MobileTariff(BaseModel):
    """A tariff plan with all available purchase periods."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    description: str | None = None
    traffic_limit_gb: int  # 0 means unlimited
    traffic_limit_label: str  # "♾️ Безлимит" or "100 ГБ"
    device_limit: int
    periods: list[MobileTariffPeriod]
    is_current: bool  # True when this is the authenticated user's active tariff


class MobileTariffsResponse(BaseModel):
    """Top-level response for GET /mobile/v1/tariffs."""

    model_config = ConfigDict(populate_by_name=True)

    tariffs: list[MobileTariff]
    current_tariff_id: int | None = None
