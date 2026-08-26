"""
Daily Google Sheets sync job.

Runs every day at 03:00 Moscow time using the same async-loop pattern
as the existing services (reporting_service, backup_service, etc.).

Usage in main.py (add inside the startup block, similar to reporting_service):

    from bot.jobs.daily_sheets_sync import sheets_sync_service
    async with timeline.stage('Google Sheets синхронизация', '📊',
                               success_message='Сервис Sheets синхронизации готов') as stage:
        try:
            await sheets_sync_service.start()
        except Exception as e:
            stage.warning(f'Ошибка запуска Sheets синхронизации: {e}')
            logger.error('❌ Ошибка запуска Sheets синхронизации', error=e)
"""

from __future__ import annotations

import asyncio
import structlog
import os
from datetime import UTC, datetime, time as datetime_time, timedelta
from zoneinfo import ZoneInfo

from app.database.database import AsyncSessionLocal
from bot.export.sheets_sync import run_daily_sync

logger = structlog.get_logger(__name__)

# Run at 03:00 Moscow time every day (same convention as backup_service and reporting_service).
_SYNC_HOUR = 3
_SYNC_MINUTE = 0
_MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class SheetsyncService:
    """
    Async-loop service that triggers run_daily_sync() once per day at 03:00 MSK.

    Lifecycle mirrors the existing service pattern (start / stop / is_running).
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        await self.stop()
        spreadsheet_id = os.getenv("SPREADSHEET_ID", "")
        creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH", "")
        if not spreadsheet_id or not creds_path:
            logger.warning(
                "Сервис Sheets синхронизации не запущен: "
                "SPREADSHEET_ID или GOOGLE_CREDENTIALS_JSON_PATH не заданы"
            )
            return
        self._task = asyncio.create_task(self._daily_loop())
        logger.info(
            "📊 Сервис Sheets синхронизации запущен: ежедневно в %02d:%02d МСК",
            _SYNC_HOUR,
            _SYNC_MINUTE,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _next_run_utc(self) -> datetime:
        """Return the next 03:00 MSK as a UTC datetime."""
        now_msk = datetime.now(_MOSCOW_TZ)
        target_msk = now_msk.replace(
            hour=_SYNC_HOUR, minute=_SYNC_MINUTE, second=0, microsecond=0
        )
        if now_msk >= target_msk:
            target_msk += timedelta(days=1)
        return target_msk.astimezone(UTC)

    async def _daily_loop(self) -> None:
        try:
            while True:
                next_run_utc = self._next_run_utc()
                delay = (next_run_utc - datetime.now(UTC)).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)

                try:
                    await self._run_once()
                    logger.info(
                        "✅ Ежедневная синхронизация Google Sheets завершена успешно"
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error(
                        "Ошибка ежедневной синхронизации Google Sheets", exc_info=exc
                    )

        except asyncio.CancelledError:
            logger.info("Сервис Sheets синхронизации остановлен")
            raise
        except Exception as exc:
            logger.error(
                "Критическая ошибка в сервисе Sheets синхронизации", exc_info=exc
            )

    async def _run_once(self) -> None:
        """Open a DB session and call run_daily_sync."""
        async with AsyncSessionLocal() as session:
            await run_daily_sync(session)


# Public entry point used by main.py (same pattern as `reporting_service` singleton).
sheets_sync_service = SheetsyncService()


async def daily_sheets_sync_job(db_session_factory) -> None:
    """
    Standalone coroutine that accepts an explicit session factory.
    Provided for callers that manage their own session lifecycle.
    """
    async with db_session_factory() as session:
        await run_daily_sync(session)
