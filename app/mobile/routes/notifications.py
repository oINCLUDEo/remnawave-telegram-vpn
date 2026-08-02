"""Mobile notifications endpoint — returns backend-driven in-app banners."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from app.cabinet.dependencies import get_current_cabinet_user
from app.database.models import User
from app.mobile.schemas.notifications import MobileNotificationListResponse, MobileNotificationResponse
from app.services.mobile_notification_store import mobile_notification_store


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    '/notifications',
    response_model=MobileNotificationListResponse,
    summary='In-app уведомления',
    description='Возвращает список активных уведомлений для мобильного клиента. Требует Bearer-токен.',
    tags=['mobile'],
)
async def get_notifications(
    user: User = Depends(get_current_cabinet_user),
) -> MobileNotificationListResponse:
    """Return active in-app notifications for the authenticated mobile user."""
    notifications = mobile_notification_store.get_active()
    items = [
        MobileNotificationResponse(
            id=n['id'],
            title=n['title'],
            body=n['body'],
            type=n.get('type', 'informational'),
            severity=n.get('severity', 'info'),
            auto_dismiss_seconds=n.get('auto_dismiss_seconds', 5),
        )
        for n in notifications
    ]
    return MobileNotificationListResponse(notifications=items)
