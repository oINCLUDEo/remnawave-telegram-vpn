"""Mobile promo code endpoint — activate a promo code for a mobile user."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.crud.user import get_user_by_telegram_id
from app.services.promocode_service import PromoCodeService


logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MobilePromoActivateRequest(BaseModel):
    """Request body for POST /mobile/v1/promocode/activate."""

    code: str = Field(..., min_length=1, max_length=50, description='Promo code to activate')


class MobilePromoActivateResponse(BaseModel):
    """Response after activating a promo code."""

    success: bool
    message: str
    balance_before_rub: float = 0.0
    balance_after_rub: float = 0.0
    bonus_description: str | None = None


# Error code → user-friendly Russian message
_ERROR_MESSAGES: dict[str, str] = {
    'not_found': 'Промокод не найден',
    'expired': 'Срок действия промокода истёк',
    'used': 'Промокод уже исчерпан',
    'already_used_by_user': 'Вы уже использовали этот промокод',
    'active_discount_exists': 'У вас уже активна скидка. Сначала деактивируйте её',
    'no_subscription_for_days': 'Этот промокод требует наличия подписки',
    'not_first_purchase': 'Этот промокод доступен только при первой покупке',
    'daily_limit': 'Слишком много активаций промокодов за сегодня',
    'user_not_found': 'Пользователь не найден',
    'server_error': 'Произошла ошибка сервера',
}


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    '/promocode/activate',
    response_model=MobilePromoActivateResponse,
    summary='Активировать промокод',
    description='Активирует промокод для авторизованного пользователя.',
    tags=['mobile'],
)
async def activate_promocode(
    request: MobilePromoActivateRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id', description='Telegram user ID'),
) -> MobilePromoActivateResponse:
    """Activate a promo code for the authenticated mobile user."""
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

            if user.status != 'active':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Учётная запись заблокирована',
                )

            promocode_service = PromoCodeService()
            result = await promocode_service.activate_promocode(
                db=db, user_id=user.id, code=request.code.strip()
            )

        await engine.dispose()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile /promocode/activate error', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обращении к базе данных',
        ) from exc

    if result.get('success'):
        balance_before = result.get('balance_before_kopeks', 0) / 100
        balance_after = result.get('balance_after_kopeks', 0) / 100
        return MobilePromoActivateResponse(
            success=True,
            message='Промокод успешно активирован',
            balance_before_rub=round(balance_before, 2),
            balance_after_rub=round(balance_after, 2),
            bonus_description=result.get('description'),
        )

    error_key = result.get('error', 'server_error')
    message = _ERROR_MESSAGES.get(error_key, 'Неизвестная ошибка')
    return MobilePromoActivateResponse(success=False, message=message)
