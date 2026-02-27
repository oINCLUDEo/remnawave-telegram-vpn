"""Server routes for the Mobile API v1.

GET /mobile/v1/servers
    Public endpoint — no authentication required.
    Returns all available VPN servers grouped by category.
    Access control is enforced by RemnaWave at connection time.

v2 behaviour:
    - Still returns the same JSON shape (MobileServersResponse).
    - Each RemnaWave internal squad is expanded into one or more
      concrete "servers" (nodes/config profiles) when the RemnaWave
      API is configured.
    - When RemnaWave is not configured or an error occurs, falls back
      to the original per-squad behaviour.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db
from app.database.crud.server_squad import get_available_server_squads
from app.mobile_api.schemas import (
    MobileServer,
    MobileServerCategory,
    MobileServersResponse,
)
from app.services.subscription_service import SubscriptionService

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


async def _load_accessible_nodes_by_squad(
    squad_uuids: list[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch accessible nodes for each internal squad from RemnaWave.

    Returns a mapping: squad_uuid -> list[accessibleNodeDict].
    On any configuration or network error, returns an empty mapping so
    the caller can fall back to DB-only behaviour.
    """
    if not squad_uuids:
        return {}

    service = SubscriptionService()
    if not service.is_configured:
        logger.info('RemnaWave not configured — no servers will be exposed to mobile API')
        return {}

    try:
        async with service.get_api_client() as api:
            tasks = {
                squad_uuid: api.get_internal_squad_accessible_nodes(squad_uuid)
                for squad_uuid in squad_uuids
                if squad_uuid
            }

            if not tasks:
                return {}

            results = await asyncio.gather(
                *tasks.values(),
                return_exceptions=True,
            )

            mapping: Dict[str, List[Dict[str, Any]]] = {}
            for squad_uuid, result in zip(tasks.keys(), results, strict=False):
                if isinstance(result, Exception):
                    logger.warning(
                        'Failed to load accessible nodes for squad',
                        squad_uuid=squad_uuid,
                        error=str(result),
                    )
                    continue

                # RemnaWaveAccessibleNode is a dataclass; we convert to dict
                # to avoid importing panel types into the mobile API layer.
                nodes: List[Dict[str, Any]] = []
                for node in result:
                    nodes.append(
                        {
                            'uuid': getattr(node, 'uuid', ''),
                            'node_name': getattr(node, 'node_name', ''),
                            'country_code': getattr(node, 'country_code', None),
                            'config_profile_uuid': getattr(
                                node, 'config_profile_uuid', ''
                            ),
                            'config_profile_name': getattr(
                                node, 'config_profile_name', ''
                            ),
                            'active_inbounds': list(
                                getattr(node, 'active_inbounds', []) or []
                            ),
                        }
                    )

                if nodes:
                    mapping[squad_uuid] = nodes

            return mapping
    except Exception as exc:  # pragma: no cover - defensive, depends on env
        logger.warning(
            'RemnaWave accessible-nodes lookup failed, falling back to DB squads',
            error=str(exc),
        )
        return {}


@router.get(
    '/servers',
    response_model=MobileServersResponse,
    summary='List available VPN servers grouped by category',
)
async def get_servers(
    db: AsyncSession = Depends(get_cabinet_db),
) -> MobileServersResponse:
    """Return all available VPN servers grouped by category.

    v2:
        - Expands each internal squad into one or more concrete servers
          (nodes/config profiles) when RemnaWave is configured.
        - Falls back to per-squad representation when RemnaWave is
          unavailable or returns no data.
    """
    squads = await get_available_server_squads(db)

    # Try to enrich squads with their accessible nodes from RemnaWave.
    squad_uuids = [s.squad_uuid for s in squads if getattr(s, 'squad_uuid', None)]
    accessible_by_squad = await _load_accessible_nodes_by_squad(squad_uuids)

    # If RemnaWave is unavailable or returned nothing, we intentionally return
    # an empty list to force proper panel configuration for the mobile app.
    if not accessible_by_squad:
        logger.warning(
            'No accessible nodes resolved from RemnaWave for any squad; '
            'mobile servers list will be empty.',
        )
        return MobileServersResponse(categories=[], total_count=0)

    grouped: dict[str, list[MobileServer]] = defaultdict(list)
    next_id = 1

    for squad in squads:
        current = squad.current_users or 0
        category = getattr(squad, 'category', None) or 'general'
        base_flag = _country_flag(squad.country_code)
        base_is_available = not squad.is_full
        base_load = _load_percent(current, squad.max_users)
        base_quality = _quality_level(current, squad.max_users)

        nodes = accessible_by_squad.get(squad.squad_uuid)
        if not nodes:
            continue

        # Expand each accessible node/config into a separate MobileServer.
        for node in nodes:
            name_parts: list[str] = []
            # Squad display name first (user-friendly, localised).
            if squad.display_name:
                name_parts.append(squad.display_name)
            # Then config profile or node name as a suffix.
            profile_name = node.get('config_profile_name') or node.get('node_name')
            if profile_name:
                name_parts.append(str(profile_name))
            server_name = ' — '.join(name_parts) if name_parts else squad.display_name

            flag = _country_flag(node.get('country_code') or squad.country_code)

            grouped[category].append(
                MobileServer(
                    id=next_id,
                    name=server_name,
                    country_code=node.get('country_code') or squad.country_code,
                    flag=flag or base_flag,
                    category=category,
                    is_available=base_is_available,
                    load_percent=base_load,
                    quality_level=base_quality,
                    match_key=str(profile_name) if profile_name else None,
                )
            )
            next_id += 1

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
