"""Schemas for the mobile /me endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MeSubscriptionInfo(BaseModel):
    """Subscription data returned by /mobile/v1/me."""

    status: str = Field(..., description='active | expired | trial | …')
    is_trial: bool = Field(False, description='True when this is a trial subscription')
    expire_at: int | None = Field(None, description='Unix timestamp of subscription expiry')
    traffic_limit_gb: int = Field(0, description='Total traffic quota in GB (0 = unlimited)')
    traffic_used_gb: float = Field(0.0, description='Traffic consumed in GB')
    subscription_url: str | None = Field(None, description='Personal subscription URL')
    device_limit: int = Field(1, description='Maximum simultaneous devices allowed')


class MeMobileResponse(BaseModel):
    """Response from GET /mobile/v1/me."""

    telegram_id: int | None = Field(None, description='Telegram user ID')
    first_name: str | None = Field(None, description='First name')
    last_name: str | None = Field(None, description='Last name')
    username: str | None = Field(None, description='Telegram username (without @)')
    has_subscription: bool = Field(False, description='True when the user has any subscription record')
    subscription: dict | None = Field(
        None,
        description='Subscription details (null when has_subscription is False)',
    )
    balance_kopeks: int = Field(0, description='Account balance in kopeks')
    balance_rub: float = Field(0.0, description='Account balance in rubles')
    balance_currency: str = Field('RUB', description='Balance currency code')
