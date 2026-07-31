"""Mobile remote-config endpoint.

Lets the admin control app-lifecycle behaviour (minimum version / forced
update, a maintenance banner, and the default split-tunneling app list)
without shipping a new app store release. Backed by the generic settings
system — see the ``MOBILE_*`` fields on ``Settings`` in ``app/config.py`` and
their ``MOBILE`` category in ``app/services/system_settings_service.py``.

Intentionally unauthenticated: the client needs this before login (forced
update / maintenance gate must show even to logged-out users) and the values
are not user-specific.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Query

from app.config import settings
from app.mobile.schemas.config import MobileRemoteConfigResponse


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    '/config',
    response_model=MobileRemoteConfigResponse,
    summary='Remote-конфигурация мобильного клиента',
    description=(
        'Публичный эндпоинт (без авторизации): минимальная поддерживаемая версия, '
        'принудительное обновление, техработы и дефолтный список приложений для '
        'сплит-туннелинга. Значения редактируются в админке мгновенно.'
    ),
    tags=['mobile'],
)
async def get_mobile_config(
    platform: str = Query('android', description='android | ios — выбирает update_url'),
) -> MobileRemoteConfigResponse:
    return MobileRemoteConfigResponse(
        min_supported_build=settings.MOBILE_MIN_SUPPORTED_BUILD,
        latest_build=settings.MOBILE_LATEST_BUILD,
        force_update=settings.MOBILE_FORCE_UPDATE,
        update_url=settings.get_mobile_update_url(platform),
        maintenance_enabled=settings.MOBILE_MAINTENANCE_MODE,
        maintenance_message=settings.MOBILE_MAINTENANCE_MESSAGE,
        blocked_apps_default=settings.get_mobile_blocked_apps_default(),
    )
