"""
Admin command handler: /sync_sheets

Triggers an immediate Google Sheets sync on demand.
Admin-only — uses the same @admin_required decorator pattern as all other
admin handlers in app/handlers/admin/*.py.
"""

from __future__ import annotations

import logging

import structlog
from aiogram import Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.utils.decorators import admin_required, error_handler
from bot.export.sheets_sync import run_daily_sync

logger = structlog.get_logger(__name__)


@admin_required
@error_handler
async def cmd_sync_sheets(
    message: types.Message,
    db_user: User,
    db: AsyncSession,
) -> None:
    """
    /sync_sheets — run Google Sheets sync immediately.
    Replies with a success or error message.
    """
    await message.answer("⏳ Запускаю синхронизацию Google Sheets…")

    try:
        await run_daily_sync(db)
        await message.answer("✅ Синхронизация завершена")
        logger.info(
            "Ручная синхронизация Google Sheets выполнена",
            admin_id=db_user.telegram_id,
        )
    except Exception as exc:
        error_text = str(exc)
        await message.answer(f"❌ Ошибка: {error_text}")
        logger.error(
            "Ошибка ручной синхронизации Google Sheets",
            admin_id=db_user.telegram_id,
            exc_info=exc,
        )


def register_handlers(dp: Dispatcher) -> None:
    dp.message.register(cmd_sync_sheets, Command("sync_sheets"))
