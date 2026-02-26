"""Mobile API v1 route assembly.

All sub-routers are collected here and included under the ``/mobile/v1`` prefix.
"""

from fastapi import APIRouter

from .profile import router as profile_router
from .servers import router as servers_router
from .tariffs import router as tariffs_router

router = APIRouter(prefix='/mobile/v1', tags=['Mobile API v1'])

router.include_router(profile_router)
router.include_router(tariffs_router)
router.include_router(servers_router)

__all__ = ['router']
