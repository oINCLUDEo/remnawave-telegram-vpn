"""Developer authentication endpoint (DEV_MODE only).

POST /mobile/v1/dev/auth
    Returns a 30-day access token for the configured DEV_USER_TELEGRAM_ID.
    Only available when DEV_MODE=true in .env.
    ⚠️  NEVER expose in production — no password or OTP check is performed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db
from app.config import settings
from app.database.crud.user import get_user_by_telegram_id

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Mobile — Dev'])


@router.post(
    '/dev/auth',
    # Hide from OpenAPI docs when not in dev mode
    include_in_schema=True,
    summary='[DEV] Get test token (DEV_MODE only)',
)
async def dev_auth(
    db: AsyncSession = Depends(get_cabinet_db),
) -> dict:
    """Return a long-lived JWT for the dev user.  Requires DEV_MODE=true."""
    if not settings.DEV_MODE:
        raise HTTPException(status_code=404, detail='Not found')

    telegram_id = settings.DEV_USER_TELEGRAM_ID
    if not telegram_id:
        raise HTTPException(
            status_code=500,
            detail='DEV_USER_TELEGRAM_ID is not set in .env',
        )

    user = await get_user_by_telegram_id(db, telegram_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f'Dev user with telegram_id={telegram_id} not found in database',
        )

    # Issue a 30-day token so the dev doesn't need to refresh constantly
    expires = datetime.now(UTC) + timedelta(days=30)
    payload = {
        'sub': str(user.id),
        'type': 'access',
        'exp': expires,
        'iat': datetime.now(UTC),
        'telegram_id': user.telegram_id,
        'dev': True,
    }
    secret = settings.get_cabinet_jwt_secret()
    token = jwt.encode(payload, secret, algorithm='HS256')

    logger.warning(
        'Dev auth token issued',
        user_id=user.id,
        telegram_id=telegram_id,
        expires=expires.isoformat(),
    )

    return {
        'access_token': token,
        'token_type': 'bearer',
        'expires_at': expires.isoformat(),
        'user_id': user.id,
        'username': user.username or user.first_name,
        'warning': 'This endpoint is for development only. Disable DEV_MODE in production.',
    }
