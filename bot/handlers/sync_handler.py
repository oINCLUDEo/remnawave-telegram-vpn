"""
Admin panel handler: Google Sheets sync button.

Adds a "📊 Google Sheets" button to the System submenu.
Flow:
  admin_sheets_sync            → show sync panel
  admin_sheets_sync_run        → sync current month
  admin_sheets_sync_run_prev   → sync previous month
"""

from __future__ import annotations

from datetime import date

import structlog
from aiogram import Dispatcher, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.utils.decorators import admin_required, error_handler
from bot.export.sheets_sync import _prev_month_date, run_daily_sync


logger = structlog.get_logger(__name__)


def _sheets_panel_keyboard() -> InlineKeyboardMarkup:
    today = date.today()
    prev = _prev_month_date(today)
    prev_label = prev.strftime("%B %Y")  # e.g. "May 2026"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text='🚀 Текущий месяц',
                callback_data='admin_sheets_sync_run',
            )],
            [InlineKeyboardButton(
                text=f'📅 Прошлый месяц ({prev_label})',
                callback_data='admin_sheets_sync_run_prev',
            )],
            [InlineKeyboardButton(text='◀️ Назад', callback_data='admin_submenu_system')],
        ]
    )


def _sheets_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔄 Запустить ещё раз', callback_data='admin_sheets_sync')],
            [InlineKeyboardButton(text='◀️ Назад', callback_data='admin_submenu_system')],
        ]
    )


@admin_required
@error_handler
async def show_sheets_panel(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    today = date.today()
    prev = _prev_month_date(today)

    await callback.message.edit_text(
        '📊 <b>Google Sheets — синхронизация</b>\n\n'
        'Записывает финансовые данные в таблицу:\n'
        '• <b>Транзакции</b> — все платежи за выбранный месяц\n'
        '• <b>По месяцам</b> — выручка, MRR, churn (upsert)\n'
        '• <b>Метрики</b> — MRR, ARPU, LTV, k-фактор и др.\n\n'
        f'Текущий месяц: <b>{today.strftime("%Y-%m")}</b>\n'
        f'Прошлый месяц: <b>{prev.strftime("%Y-%m")}</b>\n\n'
        'Автосинхронизация: каждый день в <b>03:00 МСК</b>.',
        parse_mode='HTML',
        reply_markup=_sheets_panel_keyboard(),
    )
    await callback.answer()


async def _do_sync(
    callback: types.CallbackQuery,
    db: AsyncSession,
    target_date: date | None,
    label: str,
) -> None:
    """Shared sync runner used by both current and previous month handlers."""
    await callback.answer(f'⏳ Синхронизирую {label}…')
    await callback.message.edit_text(
        f'⏳ <b>Синхронизация {label}…</b>\n\nЭто может занять несколько секунд.',
        parse_mode='HTML',
    )
    try:
        await run_daily_sync(db, target_date=target_date)
        await callback.message.edit_text(
            f'✅ <b>Синхронизация завершена</b>\n\nДанные за <b>{label}</b> записаны в Google Sheets.',
            parse_mode='HTML',
            reply_markup=_sheets_back_keyboard(),
        )
    except Exception as exc:
        await callback.message.edit_text(
            f'❌ <b>Ошибка синхронизации {label}</b>\n\n<code>{exc}</code>',
            parse_mode='HTML',
            reply_markup=_sheets_back_keyboard(),
        )
        raise


@admin_required
@error_handler
async def run_sheets_sync_current(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    today = date.today()
    await _do_sync(callback, db, target_date=None, label=today.strftime("%Y-%m"))
    logger.info('Ручная синхронизация Sheets (текущий месяц)', admin_id=db_user.telegram_id)


@admin_required
@error_handler
async def run_sheets_sync_prev(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    prev = _prev_month_date(date.today())
    await _do_sync(callback, db, target_date=prev, label=prev.strftime("%Y-%m"))
    logger.info('Ручная синхронизация Sheets (прошлый месяц)', admin_id=db_user.telegram_id)


def register_handlers(dp: Dispatcher) -> None:
    dp.callback_query.register(show_sheets_panel, F.data == 'admin_sheets_sync')
    dp.callback_query.register(run_sheets_sync_current, F.data == 'admin_sheets_sync_run')
    dp.callback_query.register(run_sheets_sync_prev, F.data == 'admin_sheets_sync_run_prev')
