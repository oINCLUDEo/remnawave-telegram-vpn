"""
Admin panel handler: Google Sheets sync button.

Adds a "📊 Google Sheets" button to the System submenu.
Flow:
  admin_sheets_sync       → show sync panel with "Запустить" button
  admin_sheets_sync_run   → run sync, show result, "◀️ Назад" button
"""

from __future__ import annotations

import structlog
from aiogram import Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.utils.decorators import admin_required, error_handler
from bot.export.sheets_sync import run_daily_sync


logger = structlog.get_logger(__name__)


def _sheets_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🚀 Запустить синхронизацию', callback_data='admin_sheets_sync_run')],
            [InlineKeyboardButton(text='◀️ Назад', callback_data='admin_submenu_system')],
        ]
    )


def _sheets_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔄 Запустить ещё раз', callback_data='admin_sheets_sync_run')],
            [InlineKeyboardButton(text='◀️ Назад', callback_data='admin_submenu_system')],
        ]
    )


@admin_required
@error_handler
async def show_sheets_panel(callback: types.CallbackQuery, db_user: User, db: AsyncSession) -> None:
    """Show the Google Sheets sync panel."""
    await callback.message.edit_text(
        '📊 <b>Google Sheets — синхронизация</b>\n\n'
        'Записывает финансовые данные текущего месяца в таблицу:\n'
        '• <b>Транзакции</b> — все платежи за месяц\n'
        '• <b>По месяцам</b> — агрегаты (выручка, MRR, churn)\n'
        '• <b>Метрики</b> — MRR, ARPU, LTV, k-фактор и др.\n\n'
        'Синхронизация также запускается автоматически каждый день в <b>03:00 МСК</b>.',
        parse_mode='HTML',
        reply_markup=_sheets_panel_keyboard(),
    )
    await callback.answer()


@admin_required
@error_handler
async def run_sheets_sync(callback: types.CallbackQuery, db_user: User, db: AsyncSession) -> None:
    """Run the sync and report the result."""
    await callback.answer('⏳ Запускаю синхронизацию…')
    await callback.message.edit_text(
        '⏳ <b>Синхронизация запущена…</b>\n\nЭто может занять несколько секунд.',
        parse_mode='HTML',
    )

    try:
        await run_daily_sync(db)
        await callback.message.edit_text(
            '✅ <b>Синхронизация завершена</b>\n\nДанные успешно записаны в Google Sheets.',
            parse_mode='HTML',
            reply_markup=_sheets_back_keyboard(),
        )
        logger.info('Ручная синхронизация Google Sheets выполнена', admin_id=db_user.telegram_id)
    except Exception as exc:
        await callback.message.edit_text(
            f'❌ <b>Ошибка синхронизации</b>\n\n<code>{exc}</code>',
            parse_mode='HTML',
            reply_markup=_sheets_back_keyboard(),
        )
        logger.error('Ошибка ручной синхронизации Google Sheets', admin_id=db_user.telegram_id, exc_info=exc)


def register_handlers(dp: Dispatcher) -> None:
    dp.callback_query.register(show_sheets_panel, F.data == 'admin_sheets_sync')
    dp.callback_query.register(run_sheets_sync, F.data == 'admin_sheets_sync_run')
