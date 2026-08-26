from __future__ import annotations

from time import monotonic

import structlog
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from structlog.contextvars import bound_contextvars


logger = structlog.get_logger('web_api')


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Логирование входящих запросов в административный API."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ctx: dict = {'http_method': request.method, 'http_path': request.url.path}
        # Bind telegram_id for mobile API requests so all log entries carry it
        tg_id = request.headers.get('X-Telegram-Id')
        if tg_id:
            ctx['telegram_id'] = tg_id
        with bound_contextvars(**ctx):
            start = monotonic()
            response: Response | None = None
            try:
                response = await call_next(request)
                return response
            except (TimeoutError, ConnectionRefusedError, OSError, OperationalError, InterfaceError) as e:
                logger.error(
                    'Database connection error on', method=request.method, path=request.url.path, e=str(e)[:200]
                )
                response = JSONResponse(
                    status_code=503,
                    content={'detail': 'Service temporarily unavailable. Please try again later.'},
                )
                return response
            finally:
                duration_ms = (monotonic() - start) * 1000
                status = response.status_code if response else 'error'
                logger.debug(
                    '-> (ms)', method=request.method, path=request.url.path, status=status, duration_ms=duration_ms
                )
