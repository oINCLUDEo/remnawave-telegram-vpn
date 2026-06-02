"""
Admin handler: /add_expense — manually record an infrastructure or marketing expense.

Flow (FSM):
  /add_expense → choose category → enter subcategory → enter amount
               → enter date (optional) → enter comment (optional) → confirm → save

Expenses are saved to the manual_expenses table and included in the next
Google Sheets sync (По месяцам columns J / M / N and Метрики margin).

Run bot/models/create_expenses_table.sql once before using this handler.
"""

from __future__ import annotations

from datetime import date

import structlog
from aiogram import Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.utils.decorators import admin_required, error_handler
from bot.models.expenses import ManualExpense


logger = structlog.get_logger(__name__)

CATEGORIES = {
    "infrastructure": "🖥 Инфраструктура",
    "marketing_ads": "📢 Реклама",
    "other": "📦 Прочее",
}


class ExpenseStates(StatesGroup):
    category = State()
    subcategory = State()
    amount = State()
    expense_date = State()
    comment = State()
    confirm = State()


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"exp_cat_{key}")]
            for key, label in CATEGORIES.items()
        ]
        + [[InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cancel")]]
    )


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="exp_save"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cancel"),
            ]
        ]
    )


def _skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="exp_skip")]
        ]
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summary(data: dict) -> str:
    cat_label = CATEGORIES.get(data.get("category", ""), data.get("category", "—"))
    return (
        f"<b>Категория:</b> {cat_label}\n"
        f"<b>Подкатегория:</b> {data.get('subcategory') or '—'}\n"
        f"<b>Сумма:</b> {data.get('amount_rub')} ₽\n"
        f"<b>Дата:</b> {data.get('expense_date') or date.today().strftime('%d.%m.%Y')}\n"
        f"<b>Комментарий:</b> {data.get('comment') or '—'}"
    )


def _parse_date(text: str) -> date | None:
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return date(*__import__("time").strptime(text.strip(), fmt)[:3])
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@admin_required
@error_handler
async def cmd_add_expense(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await state.set_state(ExpenseStates.category)
    await message.answer(
        "💸 <b>Добавить расход</b>\n\nВыберите категорию:",
        parse_mode="HTML",
        reply_markup=_category_keyboard(),
    )


@admin_required
@error_handler
async def choose_category(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    key = callback.data.removeprefix("exp_cat_")
    if key not in CATEGORIES:
        await callback.answer("Неизвестная категория", show_alert=True)
        return

    await state.update_data(category=key)
    await state.set_state(ExpenseStates.subcategory)
    await callback.message.edit_text(
        f"Категория: <b>{CATEGORIES[key]}</b>\n\n"
        "Введите <b>подкатегорию</b> (название сервера/сервиса):\n"
        "<i>Например: Aeza Amsterdam, Selectel S3, Telegram посев</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@admin_required
@error_handler
async def enter_subcategory(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(subcategory=message.text.strip())
    await state.set_state(ExpenseStates.amount)
    await message.answer(
        "Введите <b>сумму в рублях</b> (только число):",
        parse_mode="HTML",
    )


@admin_required
@error_handler
async def enter_amount(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число, например: <code>1500</code> или <code>249.90</code>", parse_mode="HTML")
        return

    await state.update_data(amount_rub=round(amount, 2))
    await state.set_state(ExpenseStates.expense_date)
    await message.answer(
        "Введите <b>дату расхода</b> в формате <code>ДД.ММ.ГГГГ</code>\n"
        "или нажмите «Пропустить» — будет использована сегодняшняя дата.",
        parse_mode="HTML",
        reply_markup=_skip_keyboard(),
    )


@admin_required
@error_handler
async def enter_date(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    parsed = _parse_date(message.text.strip())
    if not parsed:
        await message.answer(
            "❌ Не удалось распознать дату. Введите в формате <code>ДД.ММ.ГГГГ</code>, например <code>01.05.2026</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(expense_date=parsed.strftime("%d.%m.%Y"))
    await _ask_comment(message, state)


@admin_required
@error_handler
async def skip_date(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(expense_date=None)
    await callback.answer()
    await _ask_comment(callback.message, state)


async def _ask_comment(msg: types.Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.comment)
    await msg.answer(
        "Введите <b>комментарий</b> (необязательно) или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=_skip_keyboard(),
    )


@admin_required
@error_handler
async def enter_comment(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(comment=message.text.strip())
    await _show_confirm(message, state)


@admin_required
@error_handler
async def skip_comment(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(comment=None)
    await callback.answer()
    await _show_confirm(callback.message, state)


async def _show_confirm(msg: types.Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.confirm)
    data = await state.get_data()
    await msg.answer(
        f"📋 <b>Проверьте данные:</b>\n\n{_summary(data)}\n\nСохранить?",
        parse_mode="HTML",
        reply_markup=_confirm_keyboard(),
    )


@admin_required
@error_handler
async def save_expense(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    await state.clear()

    expense_date = (
        _parse_date(data["expense_date"]) if data.get("expense_date") else date.today()
    )

    expense = ManualExpense(
        amount_rub=data["amount_rub"],
        category=data["category"],
        subcategory=data.get("subcategory"),
        expense_date=expense_date,
        comment=data.get("comment"),
    )
    db.add(expense)
    await db.commit()

    logger.info(
        "Расход записан",
        admin_id=db_user.telegram_id,
        category=data["category"],
        amount_rub=data["amount_rub"],
    )
    await callback.message.edit_text(
        f"✅ <b>Записано</b>\n\n{_summary(data)}",
        parse_mode="HTML",
    )
    await callback.answer()


@admin_required
@error_handler
async def cancel_expense(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_handlers(dp: Dispatcher) -> None:
    dp.message.register(cmd_add_expense, Command("add_expense"))
    dp.callback_query.register(choose_category, F.data.startswith("exp_cat_"), ExpenseStates.category)
    dp.message.register(enter_subcategory, ExpenseStates.subcategory)
    dp.message.register(enter_amount, ExpenseStates.amount)
    dp.message.register(enter_date, ExpenseStates.expense_date)
    dp.callback_query.register(skip_date, F.data == "exp_skip", ExpenseStates.expense_date)
    dp.message.register(enter_comment, ExpenseStates.comment)
    dp.callback_query.register(skip_comment, F.data == "exp_skip", ExpenseStates.comment)
    dp.callback_query.register(save_expense, F.data == "exp_save", ExpenseStates.confirm)
    dp.callback_query.register(cancel_expense, F.data == "exp_cancel")
