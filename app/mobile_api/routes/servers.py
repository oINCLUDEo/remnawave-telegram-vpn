"""Mobile API – public server catalogue endpoint.

GET /mobile/v1/servers

Returns a list of production servers that are visible to Flutter clients
but NOT connectable (link=null, isDisabled=True).  No authentication is
required – this is a read-only public catalogue.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ServerSquad
from app.webapi.dependencies import get_db_session

from ..schemas.servers import MobileServerItem


router = APIRouter()


def _to_mobile_item(server: ServerSquad) -> MobileServerItem:
    """Convert a ServerSquad ORM object to the Flutter-compatible schema."""
    return MobileServerItem(
        uuid=server.squad_uuid,
        name=server.display_name,
        address=server.original_name or server.display_name,
        countryCode=server.country_code,
        isConnected=False,
        isDisabled=True,
        usersOnline=int(server.current_users or 0),
        link=None,
        protocol='vless',
        description=server.description,
    )


@router.get('/servers', response_model=list[MobileServerItem])
async def list_mobile_servers(
    db: AsyncSession = Depends(get_db_session),
) -> list[MobileServerItem]:
    """Return available production servers for the Flutter mobile client.

    Filters applied:
    - Only servers with ``is_available=True`` are returned (disabled /
      system / internal nodes are excluded).

    Security guarantees:
    - ``link`` is always ``null``.
    - ``isDisabled`` is always ``true``.
    - No VPN credentials are exposed.
    """
    result = await db.execute(
        select(ServerSquad)
        .where(ServerSquad.is_available.is_(True))
        .order_by(ServerSquad.sort_order, ServerSquad.display_name)
    )
    servers = result.scalars().all()
    return [_to_mobile_item(s) for s in servers]
