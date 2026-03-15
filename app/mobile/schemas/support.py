"""Pydantic schemas for mobile support ticket API."""

from __future__ import annotations

from pydantic import BaseModel


# ── Request models ────────────────────────────────────────────────────────────


class MobileCreateTicketRequest(BaseModel):
    title: str
    message: str
    logs: str | None = None


class MobileReplyRequest(BaseModel):
    message: str


# ── Response models ───────────────────────────────────────────────────────────


class MobileTicketResponse(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp


class MobileTicketMessageResponse(BaseModel):
    id: int
    message_text: str
    is_from_admin: bool
    created_at: int  # Unix timestamp


class MobileTicketDetailResponse(MobileTicketResponse):
    messages: list[MobileTicketMessageResponse]


class MobileTicketListResponse(BaseModel):
    tickets: list[MobileTicketResponse]
