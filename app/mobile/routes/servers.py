from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status

from app.mobile.schemas.servers import MobileServerListResponse, MobileServerResponse


try:  # pragma: no cover - импорт может не работать без optional-зависимостей
    from app.services.remnawave_service import (  # type: ignore
        RemnaWaveConfigurationError,
        RemnaWaveService,
    )
except Exception:  # pragma: no cover - при ошибке импорта скрываем функционал
    RemnaWaveConfigurationError = None  # type: ignore[assignment]
    RemnaWaveService = None  # type: ignore[assignment]


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
async def list_mobile_servers() -> MobileServerListResponse:
    if RemnaWaveService is None:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='RemnaWave сервис недоступен',
        )

    service = RemnaWaveService()

    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=service.configuration_error or 'RemnaWave API не настроен',
        )

    try:
        async with service.get_api_client() as api:
            hosts = await api.get_hosts()
    except Exception as exc:
        logger.error('Ошибка при получении хостов RemnaWave', error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Не удалось получить список серверов',
        ) from exc

    visible_hosts = [h for h in hosts if not h.is_hidden and not h.is_disabled]

    servers = [
        MobileServerResponse(
            uuid=host.uuid,
            name=host.name,
            address=host.address,
            countryCode=host.country_code,
            isConnected=False,
            isDisabled=True,
            usersOnline=host.users_online,
            link=None,
            protocol=host.protocol,
            description=host.description,
        )
        for host in visible_hosts
    ]

    return MobileServerListResponse(servers=servers, total=len(servers))
