"""Schemas for mobile subscription endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SubCalcRequest(BaseModel):
    """Request body for POST /mobile/v1/subscription/calc."""

    days: int = Field(..., ge=1, le=365, description='Subscription duration in days')
    traffic_gb: int = Field(..., ge=0, description='Traffic quota in GB; 0 = unlimited')
    devices: int = Field(1, ge=1, le=20, description='Number of simultaneous devices')


class SubCalcResponse(BaseModel):
    """Price calculation response."""

    price_kopeks: int = Field(..., description='Total price in kopeks')
    price_rub: float = Field(..., description='Total price in roubles')


class SubBuyRequest(BaseModel):
    """Request body for POST /mobile/v1/subscription/buy."""

    days: int = Field(..., ge=1, le=365)
    traffic_gb: int = Field(..., ge=0)
    devices: int = Field(1, ge=1, le=20)
    payment_method: str = Field('yookassa', description='Payment method: yookassa | balance')
    return_url: str | None = Field(None, description='URL to redirect to after payment')


class SubBuyResponse(BaseModel):
    """Purchase initiation response."""

    payment_url: str | None = Field(None, description='URL to open for payment (None for balance payment)')
    paid_from_balance: bool = Field(False, description='True when payment was deducted from balance directly')
    message: str = Field('', description='Human-readable status')


class SubUpgradeRequest(BaseModel):
    """Request body for POST /mobile/v1/subscription/upgrade."""

    action: str = Field(..., description='traffic | devices | days')
    value: int = Field(..., ge=1, description='Additional traffic_gb or devices or days to add')
    payment_method: str = Field('yookassa', description='Payment method: yookassa | balance')


class SubUpgradeResponse(BaseModel):
    """Upgrade response."""

    price_kopeks: int = Field(0, description='Price charged (0 for balance payment)')
    price_rub: float = Field(0.0)
    payment_url: str | None = Field(None)
    paid_from_balance: bool = Field(False)
    message: str = Field('')


class AutopayRequest(BaseModel):
    """Request body for PUT /mobile/v1/subscription/autopay."""

    enabled: bool = Field(..., description='Whether auto-renewal should be active')


class AutopayResponse(BaseModel):
    """Autopay toggle response."""

    enabled: bool
    message: str = ''


class BalanceResponse(BaseModel):
    """Response from GET /mobile/v1/balance."""

    balance_kopeks: int = Field(0)
    balance_rub: float = Field(0.0)
    autopay_enabled: bool = Field(False)
    autopay_days_before: int = Field(3)
