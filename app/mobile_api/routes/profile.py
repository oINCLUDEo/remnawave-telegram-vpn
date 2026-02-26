"""Profile route for the Mobile API v1.

GET /mobile/v1/profile
    Requires a valid Bearer token (JWT issued by the cabinet auth flow).
    Returns the authenticated user's subscription details including the
    subscription URL needed to import into the Happ VPN client.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_current_cabinet_user
from app.database.crud.subscription import get_subscription_by_user_id
from app.database.models import User

from ..schemas import MobileProfileResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Mobile — Profile'])


@router.get('/profile', response_model=MobileProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_cabinet_db),
    user: User = Depends(get_current_cabinet_user),
) -> MobileProfileResponse:
    """Return the authenticated user's profile and subscription details."""
    subscription = await get_subscription_by_user_id(db, user.id)

    if subscription is None:
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
