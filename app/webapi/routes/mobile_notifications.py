"""Admin API endpoints for managing mobile in-app notification banners.

Allows administrators to push, list and remove backend-triggered in-app
notification banners that appear in the Flutter mobile client.

Endpoints
---------
GET    /mobile-notifications           — list all active notifications
POST   /mobile-notifications           — push (add or replace) a notification
DELETE /mobile-notifications/{id}      — remove a specific notification by id
DELETE /mobile-notifications           — remove all notifications (clear)
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Path, Security, status
from pydantic import BaseModel, Field

from app.services.mobile_notification_store import mobile_notification_store

from ..dependencies import require_api_token


router = APIRouter()
logger = structlog.get_logger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────


class PushNotificationRequest(BaseModel):
    id: str = Field(..., description='Уникальный идентификатор уведомления (произвольная строка)')
    title: str = Field(..., description='Заголовок уведомления')
    body: str = Field(..., description='Текст уведомления')
    type: str = Field('informational', description='Тип: informational | persistent')
    severity: str = Field('info', description='Важность: info | warning | error | success')
    auto_dismiss_seconds: int = Field(5, ge=0, description='Секунды до автоматического скрытия (0 = не скрывать)')


class NotificationItem(BaseModel):
    id: str
    title: str
    body: str
    type: str
    severity: str
    auto_dismiss_seconds: int


class NotificationListResponse(BaseModel):
    notifications: list[NotificationItem]
    total: int


class PushNotificationResponse(BaseModel):
    ok: bool
    id: str
    total: int


class RemoveNotificationResponse(BaseModel):
    ok: bool
    removed: bool


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get(
    '',
    response_model=NotificationListResponse,
    summary='Список активных in-app уведомлений',
    dependencies=[Security(require_api_token)],
)
async def list_notifications() -> NotificationListResponse:
    """Return all currently active mobile in-app notifications."""
    items = mobile_notification_store.get_active()
    return NotificationListResponse(
        notifications=[NotificationItem(**n) for n in items],
        total=len(items),
    )


@router.post(
    '',
    response_model=PushNotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Отправить in-app уведомление',
    dependencies=[Security(require_api_token)],
)
async def push_notification(body: PushNotificationRequest) -> PushNotificationResponse:
    """Add or replace a mobile in-app notification banner.

    If a notification with the same ``id`` already exists it is replaced.
    """
    mobile_notification_store.push(
        id=body.id,
        title=body.title,
        body=body.body,
        type=body.type,
        severity=body.severity,
        auto_dismiss_seconds=body.auto_dismiss_seconds,
    )
    logger.info('Mobile in-app notification pushed', notification_id=body.id, title=body.title)
    return PushNotificationResponse(ok=True, id=body.id, total=len(mobile_notification_store))


@router.delete(
    '/{notification_id}',
    response_model=RemoveNotificationResponse,
    summary='Удалить in-app уведомление по ID',
    dependencies=[Security(require_api_token)],
)
async def remove_notification(
    notification_id: str = Path(..., description='ID уведомления для удаления'),
) -> RemoveNotificationResponse:
    """Remove a specific mobile in-app notification by its id."""
    removed = mobile_notification_store.remove(notification_id)
    logger.info('Mobile in-app notification removed', notification_id=notification_id, found=removed)
    return RemoveNotificationResponse(ok=True, removed=removed)


@router.delete(
    '',
    response_model=RemoveNotificationResponse,
    summary='Очистить все in-app уведомления',
    dependencies=[Security(require_api_token)],
)
async def clear_notifications() -> RemoveNotificationResponse:
    """Remove all active mobile in-app notifications."""
    mobile_notification_store.clear()
    logger.info('All mobile in-app notifications cleared')
    return RemoveNotificationResponse(ok=True, removed=True)
