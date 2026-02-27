"""Mobile API v1 route assembly.

All sub-routers are collected here and included under the ``/mobile/v1`` prefix.
"""

from fastapi import APIRouter

from app.config import settings

from .dev_auth import router as dev_auth_router
from .profile import router as profile_router
from .servers import router as servers_router
from .tariffs import router as tariffs_router
from .vpn_config import router as vpn_config_router

router = APIRouter(prefix='/mobile/v1', tags=['Mobile API v1'])

router.include_router(profile_router)
router.include_router(tariffs_router)
router.include_router(servers_router)
router.include_router(vpn_config_router)

# Dev auth endpoint — always included but returns 404 when DEV_MODE=false
router.include_router(dev_auth_router)

__all__ = ['router']
