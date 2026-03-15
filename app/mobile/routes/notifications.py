"""Mobile notifications endpoint — returns backend-driven in-app banners."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.crud.user import get_user_by_telegram_id
from app.mobile.schemas.notifications import MobileNotificationListResponse, MobileNotificationResponse
from app.services.mobile_notification_store import mobile_notification_store


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    '/notifications',
    response_model=MobileNotificationListResponse,
    summary='In-app уведомления',
    description=(
        'Возвращает список активных уведомлений для мобильного клиента. '
        'Требует заголовок X-Telegram-Id с Telegram ID пользователя.'
    ),
    tags=['mobile'],
)
async def get_notifications(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id', description='Telegram user ID'),
) -> MobileNotificationListResponse:
    """Return active in-app notifications for the authenticated mobile user."""
    try:
        db_url = settings.get_database_url()
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

        async with async_session() as db:
            user = await get_user_by_telegram_id(db, x_telegram_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Пользователь не найден',
                )

        await engine.dispose()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile /notifications DB error', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обращении к базе данных',
        ) from exc

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
