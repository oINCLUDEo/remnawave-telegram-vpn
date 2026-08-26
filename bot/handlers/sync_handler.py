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
from bot.export.sheets_sync import _prev_month_date, run_daily_sync, run_full_history_sync


logger = structlog.get_logger(__name__)


def _sheets_panel_keyboard() -> InlineKeyboardMarkup:
    today = date.today()
    prev = _prev_month_date(today)
    prev_label = prev.strftime("%Y-%m")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🚀 Текущий месяц', callback_data='admin_sheets_sync_run')],
            [InlineKeyboardButton(
                text=f'📅 Прошлый месяц ({prev_label})',
                callback_data='admin_sheets_sync_run_prev',
            )],
            [InlineKeyboardButton(
                text='📚 Все месяцы (полная история)',
                callback_data='admin_sheets_sync_all',
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


@admin_required
@error_handler
async def run_sheets_sync_all(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    """Sync every month from the first payment to today."""
    await callback.answer('⏳ Запускаю полную историческую синхронизацию...')
    msg = await callback.message.edit_text(
        '⏳ <b>Синхронизация всей истории...</b>\n\n'
        'Определяю первый платёж...',
        parse_mode='HTML',
    )

    done_months: list[str] = []

    async def on_progress(month_str: str, done: int, total: int) -> None:
        done_months.append(month_str)
        # Update every 3 months to avoid Telegram rate limit
        if done % 3 == 0 or done == total:
            recent = done_months[-6:]
            lines = [f'⏳ <b>Синхронизация: {done}/{total}</b>\n']
            for m in recent:
                lines.append(f'✅ {m}')
            if done < total:
                lines.append('⏳ ...')
            try:
                await msg.edit_text('\n'.join(lines), parse_mode='HTML')
            except Exception:
                pass

    try:
        result = await run_full_history_sync(db, progress_callback=on_progress)
        await msg.edit_text(
            f'✅ <b>Полная синхронизация завершена</b>\n\n'
            f'Обработано месяцев: {result["synced"]} из {result.get("total", "?")}',
            parse_mode='HTML',
            reply_markup=_sheets_back_keyboard(),
        )
        logger.info(
            'Полная синхронизация Sheets завершена',
            synced=result['synced'],
            admin_id=db_user.telegram_id,
        )
    except Exception as exc:
        await msg.edit_text(
            f'❌ <b>Ошибка полной синхронизации</b>\n\n<code>{exc}</code>',
            parse_mode='HTML',
            reply_markup=_sheets_back_keyboard(),
        )
        logger.error('Ошибка полной синхронизации Sheets', admin_id=db_user.telegram_id, exc_info=exc)


def register_handlers(dp: Dispatcher) -> None:
    dp.callback_query.register(show_sheets_panel, F.data == 'admin_sheets_sync')
    dp.callback_query.register(run_sheets_sync_current, F.data == 'admin_sheets_sync_run')
    dp.callback_query.register(run_sheets_sync_prev, F.data == 'admin_sheets_sync_run_prev')
    dp.callback_query.register(run_sheets_sync_all, F.data == 'admin_sheets_sync_all')
