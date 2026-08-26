"""Redis-backed one-time token store for mobile Telegram authentication.

Tokens are stored under the key  ``mobile_auth:{token}``  as JSON with a
short TTL.  The bot's /start handler writes the "verified" state; the mobile
app polls the check endpoint until it sees a verified token.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import settings


logger = structlog.get_logger(__name__)

_REDIS_PREFIX = 'mobile_auth:'
TOKEN_TTL_SECONDS = 300  # 5 minutes
MOBILE_AUTH_START_PREFIX = 'mobile_auth_'

def _make_key(token: str) -> str:
    return f'{_REDIS_PREFIX}{token}'


def generate_token() -> str:
    """Return a new random URL-safe token string."""
    return uuid.uuid4().hex


async def create_auth_token() -> str:
    """Create a pending token in Redis and return it.

    Stores ``{"status": "pending"}`` under ``mobile_auth:<token>``.
    """
    token = generate_token()
    try:
        client = aioredis.from_url(settings.REDIS_URL)
        await client.set(_make_key(token), json.dumps({'status': 'pending'}), ex=TOKEN_TTL_SECONDS)
        await client.aclose()
        logger.debug('Mobile auth token created', token=token[:8])
    except Exception as exc:
        logger.error('Failed to create mobile auth token in Redis', error=exc)
        raise
    return token


async def get_auth_token(token: str) -> dict[str, Any] | None:
    """Return the stored token data, or *None* if missing / expired."""
    try:
        client = aioredis.from_url(settings.REDIS_URL)
        raw = await client.get(_make_key(token))
        await client.aclose()
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.error('Failed to read mobile auth token from Redis', error=exc)
        return None


async def verify_auth_token(
    token: str,
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
) -> bool:
    """Mark an existing pending token as verified with user data.

    Returns True if the token existed (and was updated), False otherwise.
    """
    try:
        client = aioredis.from_url(settings.REDIS_URL)
        key = _make_key(token)

        # Check that the token exists before overwriting.
        existing = await client.get(key)
        if existing is None:
            await client.aclose()
            logger.warning('Mobile auth token not found or expired', token=token[:8])
            return False

        payload = {
            'status': 'verified',
            'telegram_id': telegram_id,
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
        }
        # Keep the remaining TTL so the app can still poll.
        ttl = await client.ttl(key)
        remaining = max(ttl, 60)  # keep at least 60 s for the poll
        await client.set(key, json.dumps(payload), ex=remaining)
        await client.aclose()
        logger.info('Mobile auth token verified', token=token[:8], telegram_id=telegram_id)
        return True
    except Exception as exc:
        logger.error('Failed to verify mobile auth token', error=exc)
        return False


async def delete_auth_token(token: str) -> None:
    """Delete a token from Redis (call after successful poll)."""
    try:
        client = aioredis.from_url(settings.REDIS_URL)
        await client.delete(_make_key(token))
        await client.aclose()
    except Exception:
        pass
