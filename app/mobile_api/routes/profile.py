"""Profile route for the Mobile API v1.

GET /mobile/v1/profile
    Requires a valid Bearer token (JWT issued by the cabinet auth flow).
    Returns the authenticated user's subscription details pulled from both
    the bot's local database and, as a live fallback, the RemnaWave panel.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_current_cabinet_user
from app.config import settings
from app.database.crud.subscription import get_subscription_by_user_id
from app.database.models import User
from app.external.remnawave_api import RemnaWaveAPI

from ..schemas import MobileProfileResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Mobile — Profile'])


async def _profile_from_remnawave(user: User) -> MobileProfileResponse | None:
    """Query RemnaWave panel directly for a user's live subscription data.

    Used as a fallback when no subscription row exists in the bot's local DB
    (e.g. fresh dev accounts that have never interacted with the Telegram bot).
    Returns *None* if RemnaWave is not configured or the user is not found.
    """
    base_url = settings.REMNAWAVE_API_URL
    api_key = settings.REMNAWAVE_API_KEY
    if not base_url or not api_key:
        return None

    telegram_id = getattr(user, 'telegram_id', None)
    if not telegram_id:
        return None

    try:
        api = RemnaWaveAPI(
            base_url=base_url,
            api_key=api_key,
            secret_key=settings.REMNAWAVE_SECRET_KEY,
        )
        async with api:
            # Hard 4-second timeout — the RemnaWave API client retries up to 3×
            # with exponential back-off (7+ s total), which is unacceptable for
            # a user-facing profile endpoint.
            async with asyncio.timeout(4.0):
                rw_users = await api.get_user_by_telegram_id(int(telegram_id))
    except Exception as exc:
        logger.warning('RemnaWave fallback failed for profile', error=str(exc))
        return None

    if not rw_users:
        return None

    rw = rw_users[0]  # take first matching user
    used_bytes = rw.used_traffic_bytes or 0
    limit_bytes = rw.traffic_limit_bytes or 0
    used_gb = round(used_bytes / (1024 ** 3), 2)
    limit_gb = round(limit_bytes / (1024 ** 3), 2)
    traffic_percent = (
        min(100.0, round(used_gb / limit_gb * 100, 1)) if limit_gb > 0 else 0.0
    )
    is_active = rw.status.value == 'ACTIVE' if rw.status else False

    return MobileProfileResponse(
        username=user.username or user.first_name,
        subscription_url=rw.subscription_url or None,
        traffic_used_gb=used_gb,
        traffic_limit_gb=int(limit_gb),
        traffic_used_percent=traffic_percent,
        expires_at=rw.expire_at if rw.expire_at else None,
        is_active=is_active,
        status='active' if is_active else 'expired',
    )


@router.get('/profile', response_model=MobileProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_cabinet_db),
    user: User = Depends(get_current_cabinet_user),
) -> MobileProfileResponse:
    """Return the authenticated user's profile and subscription details."""
    subscription = await get_subscription_by_user_id(db, user.id)

    if subscription is None:
        # No local DB row — try to pull live data from RemnaWave panel
        rw_profile = await _profile_from_remnawave(user)
        if rw_profile:
            return rw_profile
        return MobileProfileResponse(
            username=user.username or user.first_name,
            subscription_url=None,
            traffic_used_gb=0.0,
            traffic_limit_gb=0,
            traffic_used_percent=0.0,
            expires_at=None,
            is_active=False,
            status='no_subscription',
        )

    traffic_percent = 0.0
    if subscription.traffic_limit_gb and subscription.traffic_limit_gb > 0:
        used = subscription.traffic_used_gb or 0.0
        traffic_percent = min(100.0, round(used / subscription.traffic_limit_gb * 100, 1))

    expires_at: datetime | None = None
    if subscription.end_date is not None:
        expires_at = subscription.end_date

    return MobileProfileResponse(
        username=user.username or user.first_name,
        subscription_url=subscription.subscription_url,
        traffic_used_gb=round(subscription.traffic_used_gb or 0.0, 2),
        traffic_limit_gb=subscription.traffic_limit_gb or 0,
        traffic_used_percent=traffic_percent,
        expires_at=expires_at,
        is_active=subscription.is_active,
        status=subscription.actual_status,
    )
