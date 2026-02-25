"""Server routes for the Mobile API v1.

GET /mobile/v1/servers
    Public endpoint — no authentication required.
    Anonymous callers see servers available to the default promo group.
    Authenticated callers see servers available to their own promo group.
    Servers are grouped by their ``category`` field and sorted by a
    canonical display order (whitelist → youtube → premium → general).
"""

from __future__ import annotations

from collections import defaultdict

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_optional_cabinet_user
from app.database.crud.promo_group import get_default_promo_group
from app.database.crud.server_squad import get_available_server_squads
from app.mobile_api.schemas import (
    MobileServer,
    MobileServerCategory,
    MobileServersResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# Human-readable labels for known category slugs.
# Fall back to (slug.capitalize(), '') for unknown slugs.
_CATEGORY_LABELS: dict[str, tuple[str, str]] = {
    'general': ('Общие серверы', 'Стандартный доступ'),
    'whitelist': ('Белые списки', 'Для доступа везде'),
    'youtube': ('YouTube', 'Оптимизировано для YouTube'),
    'premium': ('Premium', 'Высокоскоростные серверы'),
}

# Preferred display order — unlisted slugs are appended last.
_CATEGORY_ORDER = ['whitelist', 'youtube', 'premium', 'general']


def _country_flag(code: str | None) -> str:
    """Convert an ISO 3166-1 alpha-2 country code to the corresponding flag emoji."""
    if not code or len(code) != 2:
        return '🌐'
    a, b = code.upper()
    return chr(0x1F1E6 + ord(a) - ord('A')) + chr(0x1F1E6 + ord(b) - ord('A'))


def _quality_level(current: int, max_users: int | None) -> int:
    """Return a 1–5 quality indicator (5 = best / no load)."""
    if max_users is None or max_users == 0:
        return 5
    load = current / max_users
    if load < 0.3:
        return 5
    if load < 0.5:
        return 4
    if load < 0.7:
        return 3
    if load < 0.9:
        return 2
    return 1


def _load_percent(current: int, max_users: int | None) -> int:
    if max_users is None or max_users == 0:
        return 0
    return min(100, int(current / max_users * 100))


@router.get(
    '/servers',
    response_model=MobileServersResponse,
    summary='List available VPN servers grouped by category',
)
async def get_servers(
    user=Depends(get_optional_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> MobileServersResponse:
    """Return available VPN servers grouped by category.

    The server list is filtered by promo group so users only see servers
    that their subscription tier is allowed to access.  Anonymous callers
    fall back to the default promo group (the one every new user receives).
    """
    # Resolve the promo group id to use for server visibility filtering.
    if user and getattr(user, 'promo_group_id', None):
        promo_group_id: int | None = user.promo_group_id
    else:
        default_pg = await get_default_promo_group(db)
        promo_group_id = default_pg.id if default_pg else None

    squads = await get_available_server_squads(db, promo_group_id=promo_group_id)

    # Group servers by category.
    grouped: dict[str, list[MobileServer]] = defaultdict(list)
    for squad in squads:
        current = squad.current_users or 0
        category = getattr(squad, 'category', None) or 'general'
        grouped[category].append(
            MobileServer(
                id=squad.id,
                name=squad.display_name,
                country_code=squad.country_code,
                flag=_country_flag(squad.country_code),
                category=category,
                is_available=not squad.is_full,
                load_percent=_load_percent(current, squad.max_users),
                quality_level=_quality_level(current, squad.max_users),
            )
        )

    # Build the response category list.
    categories: list[MobileServerCategory] = []
    for slug, servers in grouped.items():
        label, subtitle = _CATEGORY_LABELS.get(slug, (slug.capitalize(), ''))
        categories.append(
            MobileServerCategory(
                id=slug,
                name=label,
                subtitle=subtitle,
                server_count=len(servers),
                servers=sorted(servers, key=lambda s: s.name),
            )
        )

    # Sort categories by canonical display order.
    categories.sort(
        key=lambda c: _CATEGORY_ORDER.index(c.id) if c.id in _CATEGORY_ORDER else 99
    )

    return MobileServersResponse(
        categories=categories,
        total_count=sum(c.server_count for c in categories),
    )
