"""VPN config proxy route for Mobile API v1.

GET /mobile/v1/vpn-config
    Requires a valid Bearer token (JWT issued by the cabinet auth flow).
    Fetches the user's Remnawave subscription URL server-side, base64-decodes
    the content, and returns a clean JSON list of proxy links.

    This is more reliable than having Flutter fetch the subscription URL
    directly, because:
    - The bot container is on the same network as the Remnawave panel and can
      resolve internal Docker hostnames.
    - The backend handles all base64 / MIME / encoding edge cases once.
    - Flutter just receives a ready-to-use list of vless:// / vmess:// links.
"""

from __future__ import annotations

import asyncio
import base64

import aiohttp
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_current_cabinet_user
from app.config import settings
from app.database.models import User
from app.external.remnawave_api import RemnaWaveAPI

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Mobile — VPN Config'])

_KNOWN_SCHEMES = (
    'vless://', 'vmess://', 'trojan://', 'ss://',
    'hysteria2://', 'tuic://', 'hysteria://',
)


class MobileVpnConfigResponse(BaseModel):
    """Response for GET /mobile/v1/vpn-config."""

    proxy_links: list[str]       # raw vless:// / vmess:// etc. strings
    total: int                   # total number of returned proxy links
    subscription_url: str | None = None  # the source URL (for debugging)


def _decode_subscription_body(raw: str) -> list[str]:
    """Decode a Remnawave subscription response body into a list of proxy links.

    The body may be:
    - MIME base64 (line-wrapped every 76 chars, standard base64 alphabet)
    - URL-safe base64 (RFC 4648 §5, `-` and `_`)
    - Plain-text proxy links (one per line)
    """
    # Strip ALL whitespace so MIME line-wrapping doesn't break decoders.
    compact = raw.replace('\n', '').replace('\r', '').replace(' ', '')

    def _pad(s: str) -> str:
        rem = len(s) % 4
        return s if rem == 0 else s + '=' * (4 - rem)

    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(_pad(compact)).decode('utf-8')
            links = [
                l.strip()
                for l in decoded.splitlines()
                if l.strip().startswith(_KNOWN_SCHEMES)
            ]
            if links:
                return links
        except Exception:
            continue

    # Not base64 — treat as plain-text proxy links
    return [
        l.strip()
        for l in raw.splitlines()
        if l.strip().startswith(_KNOWN_SCHEMES)
    ]


async def _fetch_subscription_content(url: str) -> str:
    """HTTP GET the subscription URL and return the raw response body."""
    timeout = aiohttp.ClientTimeout(total=10, connect=5)
    headers = {
        'User-Agent': 'v2rayN/6.0',
        'Accept': '*/*',
    }
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.text()


async def _get_subscription_url(user: User) -> str | None:
    """Return the user's personal subscription URL from RemnaWave."""
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
            async with asyncio.timeout(5.0):
                users = await api.get_user_by_telegram_id(int(telegram_id))
    except Exception as exc:
        logger.warning('RemnaWave lookup failed for vpn-config', error=str(exc))
        return None

    if not users:
        return None

    return users[0].subscription_url or None


@router.get('/vpn-config', response_model=MobileVpnConfigResponse)
async def get_vpn_config(
    db: AsyncSession = Depends(get_cabinet_db),
    user: User = Depends(get_current_cabinet_user),
) -> MobileVpnConfigResponse:
    """Return a list of parsed proxy links for the authenticated user.

    Flow:
    1. Resolve the user's subscription URL from RemnaWave (internal API).
    2. Fetch the subscription content (HTTP GET server-side).
    3. Base64-decode and extract vless:// / vmess:// etc. lines.
    4. Return as JSON list.
    """
    sub_url = await _get_subscription_url(user)
    if not sub_url:
        raise HTTPException(
            status_code=404,
            detail='Subscription not found. Make sure your account is active in RemnaWave.',
        )

    try:
        raw_body = await _fetch_subscription_content(sub_url)
    except aiohttp.ClientResponseError as exc:
        logger.error('Failed to fetch subscription content', url=sub_url, status=exc.status)
        raise HTTPException(
            status_code=502,
            detail=f'Could not fetch subscription content (HTTP {exc.status})',
        ) from exc
    except Exception as exc:
        logger.error('Subscription fetch error', url=sub_url, error=str(exc))
        raise HTTPException(status_code=502, detail='Failed to fetch subscription content') from exc

    proxy_links = _decode_subscription_body(raw_body)
    if not proxy_links:
        logger.warning(
            'No proxy links parsed from subscription',
            url=sub_url,
            body_len=len(raw_body),
        )
        raise HTTPException(
            status_code=422,
            detail=f'Could not parse any proxy links from subscription (body length: {len(raw_body)})',
        )

    return MobileVpnConfigResponse(
        proxy_links=proxy_links,
        total=len(proxy_links),
        subscription_url=sub_url,
    )
