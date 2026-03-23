"""Mobile referral endpoint — returns referral code, link, and basic stats."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.crud.user import get_user_by_telegram_id
from app.database.models import User


logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MobileReferralResponse(BaseModel):
    """Response for GET /mobile/v1/referral."""

    referral_code: str = Field(..., description='Unique referral code for this user')
    referral_link: str = Field(..., description='Bot referral deep-link')
    total_referrals: int = Field(0, description='Total number of invited users')
    total_earnings_kopeks: int = Field(0, description='Total earnings from referrals in kopeks')
    total_earnings_rubles: float = Field(0.0, description='Total earnings from referrals in rubles')
    commission_percent: int = Field(0, description='Commission percentage for referral earnings')
    program_enabled: bool = Field(True, description='Whether the referral program is enabled')


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get(
    '/referral',
    response_model=MobileReferralResponse,
    summary='Реферальная программа',
    description='Возвращает реферальный код и статистику пользователя.',
    tags=['mobile'],
)
async def get_referral(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id', description='Telegram user ID'),
) -> MobileReferralResponse:
    """Return referral info for the authenticated mobile user."""
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

            referral_code = getattr(user, 'referral_code', None) or ''
            commission_percent = int(getattr(user, 'referral_commission_percent', None) or 0)

            # Count total invited users
            total_referrals_result = await db.execute(
                select(func.count(User.id)).where(User.referred_by_id == user.id)
            )
            total_referrals = total_referrals_result.scalar() or 0

            # Sum total earnings from referrals
            from sqlalchemy import text

            earnings_result = await db.execute(
                text(
                    'SELECT COALESCE(SUM(amount_kopeks), 0) FROM referral_earnings WHERE user_id = :uid'
                ),
                {'uid': user.id},
            )
            total_earnings_kopeks = int(earnings_result.scalar() or 0)

        await engine.dispose()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile /referral DB error', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обращении к базе данных',
        ) from exc

    referral_link = ''
    if referral_code:
        try:
            referral_link = settings.get_referral_link(referral_code)
        except Exception:
            bot_username = (settings.BOT_USERNAME or '').strip().lstrip('@')
            if bot_username:
                referral_link = f'https://t.me/{bot_username}?start=ref_{referral_code}'

    return MobileReferralResponse(
        referral_code=referral_code,
        referral_link=referral_link,
        total_referrals=int(total_referrals),
        total_earnings_kopeks=total_earnings_kopeks,
        total_earnings_rubles=round(total_earnings_kopeks / 100, 2),
        commission_percent=commission_percent,
        program_enabled=settings.is_referral_program_enabled(),
    )
