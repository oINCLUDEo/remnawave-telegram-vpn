"""Schemas for the mobile subscription endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SubscriptionSelectionRequest(BaseModel):
    """Subscription configuration selected by the user."""

    period_id: str = Field(..., description='Period identifier, e.g. "days:30"')
    traffic_value: int | None = Field(None, description='Selected traffic quota in GB')
    devices: int | None = Field(None, description='Number of simultaneous devices')
    servers: list[str] | None = Field(None, description='List of server squad UUIDs')


class SubscriptionBuyRequest(SubscriptionSelectionRequest):
    """Request body for POST /mobile/v1/subscription/buy."""



class SubscriptionUpgradeRequest(BaseModel):
    """Request body for POST /mobile/v1/subscription/upgrade."""

    period_id: str | None = Field(None, description='Period to extend by, e.g. "days:30"')
    traffic_add: int | None = Field(None, description='Extra traffic GB to add')
    devices_add: int | None = Field(None, description='Extra device slots to add')
    servers: list[str] | None = Field(None, description='Replacement server UUIDs')


class AutopayRequest(BaseModel):
    """Request body for PUT /mobile/v1/subscription/autopay."""

    enabled: bool = Field(..., description='Enable or disable autopay')


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class SubscriptionOptionsResponse(BaseModel):
    """Response from GET /mobile/v1/subscription/options."""

    has_subscription: bool
    context: dict[str, Any]


class CalcResponse(BaseModel):
    """Response from POST /mobile/v1/subscription/calc."""

    total_kopeks: int
    total_rub: float
    details: dict[str, Any]
    preview: dict[str, Any]


class BuyResponse(BaseModel):
    """Response from POST /mobile/v1/subscription/buy."""

    status: str = Field(..., description='"success" | "payment_required" | "error"')
    message: str | None = None
    payment_url: str | None = Field(None, description='YooKassa confirmation URL when payment is required')
    amount_kopeks: int | None = None
    subscription: dict[str, Any] | None = None


class UpgradeResponse(BaseModel):
    """Response from POST /mobile/v1/subscription/upgrade."""

    status: str
    message: str | None = None
    payment_url: str | None = None
    amount_kopeks: int | None = None
    subscription: dict[str, Any] | None = None


class BalanceResponse(BaseModel):
    """Response from GET /mobile/v1/balance."""

    balance_kopeks: int
    balance_rub: float
    currency: str = 'RUB'


class AutopayResponse(BaseModel):
    """Response from PUT /mobile/v1/subscription/autopay."""

    autopay_enabled: bool
    message: str


class BalanceTopupRequest(BaseModel):
    """Request body for POST /mobile/v1/balance/topup."""

    amount_kopeks: int = Field(..., ge=100, description='Top-up amount in kopeks (min 100 = 1 RUB)')


class BalanceTopupResponse(BaseModel):
    """Response from POST /mobile/v1/balance/topup."""

    status: str
    payment_url: str | None = None
    message: str | None = None
    amount_kopeks: int | None = None
