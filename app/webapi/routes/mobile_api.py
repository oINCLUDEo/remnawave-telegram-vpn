"""Публичные маршруты мобильного API для Flutter-клиента.

Все эндпоинты в этом модуле доступны без аутентификации —
они предназначены исключительно для чтения публичного каталога серверов.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.server_squad import get_available_server_squads
from app.database.models import ServerSquad

from ..dependencies import get_db_session
from ..schemas.mobile_api import MobileServerListResponse, MobileServerResponse


router = APIRouter()


def _to_mobile_server(server: ServerSquad) -> MobileServerResponse:
    """Преобразует ORM-объект сервера в схему мобильного API."""
    return MobileServerResponse(
        uuid=server.squad_uuid,
        name=server.display_name,
        address=None,
        country_code=server.country_code,
        is_connected=bool(server.is_available),
        is_disabled=True,
        users_online=int(server.current_users or 0),
        link=None,
        protocol=None,
        description=server.description,
    )


@router.get(
    '/servers',
    response_model=MobileServerListResponse,
    summary='Список публичных серверов',
    description=(
        'Возвращает список доступных серверов в режиме публичного каталога. '
        'Серверы видны, но не позволяют подключиться: '
        '``link`` всегда ``null``, ``isDisabled`` всегда ``true``. '
        'Аутентификация не требуется.'
    ),
)
async def list_public_servers(
    db: AsyncSession = Depends(get_db_session),
) -> MobileServerListResponse:
    servers = await get_available_server_squads(db)
    return MobileServerListResponse(
        servers=[_to_mobile_server(s) for s in servers],
    )
