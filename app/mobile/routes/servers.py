from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db
from app.database.crud.server_squad import get_available_server_squads
from app.mobile.schemas.servers import MobileServerListResponse, MobileServerResponse


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    '/servers',
    response_model=MobileServerListResponse,
    summary='Список публичных серверов',
    description=(
        'Возвращает публичный каталог серверов для Flutter-клиента. '
        'Серверы отображаются только для предпросмотра: link всегда null, isDisabled всегда true.'
    ),
    tags=['mobile'],
)
async def list_mobile_servers(db: AsyncSession = Depends(get_cabinet_db)) -> MobileServerListResponse:
    # Sourced from our own curated ServerSquad catalog (same one real subscribers'
    # tariffs are built from), NOT the RemnaWave panel's raw host list — the panel
    # exposes every host including internal/reserve ones (e.g. "4G · Резерв 1")
    # that were never meant to appear in a public preview, and its host.description
    # is unrelated to the admin-authored ServerSquad.description the app's category
    # matcher (bypass/unlimited/other) actually looks at.
    squads = await get_available_server_squads(db)

    servers = [
        MobileServerResponse(
            uuid=squad.squad_uuid,
            name=squad.display_name,
            address=squad.squad_uuid,
            countryCode=squad.country_code or '',
            isConnected=False,
            isDisabled=True,
            usersOnline=squad.current_users or 0,
            link=None,
            protocol='vless',
            description=squad.description,
        )
        for squad in squads
    ]

    return MobileServerListResponse(servers=servers, total=len(servers))
