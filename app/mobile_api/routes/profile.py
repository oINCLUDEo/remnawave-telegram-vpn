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
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
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
                if not rw_users:
                    return None

                rw = rw_users[0]  # take first matching user
    except Exception as exc:
        logger.warning('RemnaWave fallback failed for profile', error=str(exc))
        return None

    if rw is None:
        return None
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
        # The actual subscription body is served by the backend at
        # /mobile/v1/profile/subscription so the mobile app never has
        # to talk to the RemnaWave panel directly.
        subscription_url='/mobile/v1/profile/subscription',
        traffic_used_gb=used_gb,
        traffic_limit_gb=int(limit_gb),
        traffic_used_percent=traffic_percent,
        expires_at=rw.expire_at if rw.expire_at else None,
        is_active=is_active,
        status='active' if is_active else 'expired',
    )


@router.get(
    '/profile/subscription',
    response_class=PlainTextResponse,
    summary='Return raw RemnaWave subscription content for the current user',
)
async def get_profile_subscription(
    user: User = Depends(get_current_cabinet_user),
) -> PlainTextResponse:
    """Return the raw subscription body for the authenticated user.

    The mobile app uses this endpoint as the `subscription_url` so it never
    needs to talk to the RemnaWave panel directly or know its API key.
    """
    telegram_id = getattr(user, 'telegram_id', None)
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User has no telegram_id bound for RemnaWave lookup',
        )

    try:
        api = RemnaWaveAPI(
            base_url=settings.REMNAWAVE_API_URL,
            api_key=settings.REMNAWAVE_API_KEY,
            secret_key=settings.REMNAWAVE_SECRET_KEY,
        )
        async with api:
            async with asyncio.timeout(6.0):
                rw_users = await api.get_user_by_telegram_id(int(telegram_id))
                if not rw_users:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail='RemnaWave user not found for this telegram_id',
                    )

                rw = rw_users[0]

                if not rw.subscription_url:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail='RemnaWave subscription URL is not set for this user',
                    )

                # Descriptive HWID bound to this backend user; RemnaWave uses it
                # for device limits / tracking.
                hwid = f'ulya-vpn-mobile-user-{user.id}'

                headers = {
                    'User-Agent': 'UlyaVPN/1.0.0/Flutter',
                    'X-HWID': hwid,
                }

                if api.session is None:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail='RemnaWave client session is not initialized',
                    )

                # Call the public subscription URL (sub.example.com/<uuid>),
                # letting RemnaWave return the raw (base64/plain) subscription
                # content that flutter_v2ray can parse via share links.
                async with api.session.get(rw.subscription_url, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise HTTPException(
                            status_code=resp.status,
                            detail=f'RemnaWave v2ray-json endpoint responded with {resp.status}',
                        )
                    if not text or not text.strip():
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail='RemnaWave returned an empty v2ray-json body',
                        )
                    body = text
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning('Failed to load RemnaWave subscription for profile', error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Failed to load subscription from RemnaWave panel',
        ) from exc

    return PlainTextResponse(body, media_type='text/plain; charset=utf-8')


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
        # Always use the internal proxying endpoint so the mobile app never
        # needs to know the RemnaWave host or API keys.
        subscription_url='/mobile/v1/profile/subscription',
        traffic_used_gb=round(subscription.traffic_used_gb or 0.0, 2),
        traffic_limit_gb=subscription.traffic_limit_gb or 0,
        traffic_used_percent=traffic_percent,
        expires_at=expires_at,
        is_active=subscription.is_active,
        status=subscription.actual_status,
    )
