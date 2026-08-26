"""Pydantic schemas for mobile in-app notification responses."""

from __future__ import annotations

from pydantic import BaseModel


class MobileNotificationResponse(BaseModel):
    """A single in-app notification entry."""

    id: str
    title: str
    body: str
    type: str = 'informational'  # one_time | persistent | informational
    severity: str = 'info'  # info | warning | error | success
    auto_dismiss_seconds: int = 5


class MobileNotificationListResponse(BaseModel):
    """Response containing active in-app notifications."""

    notifications: list[MobileNotificationResponse]
