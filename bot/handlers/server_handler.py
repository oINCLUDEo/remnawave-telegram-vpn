"""
Admin handler: Infrastructure server management.

Accessible via: Система → 🖥 Серверы

Features:
  - View all servers with upcoming payment dates
  - Add server (fixed or hourly billing)
  - Edit / deactivate server
  - Fixed billing: monthly_cost_rub + billing_day → auto-computes next_payment_date
  - Hourly billing: estimated_hourly_rate_rub for forecasting;
    actual monthly cost entered via /add_expense when known
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import structlog
from aiogram import Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.utils.decorators import admin_required, error_handler
from bot.models.servers import InfrastructureServer


logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------

class ServerStates(StatesGroup):
    billing_type = State()
    name = State()
    provider = State()
    location = State()
    # fixed
    monthly_cost = State()
    billing_day = State()
    # hourly
    hourly_rate = State()
    # common
    remind_days = State()
    notes = State()
    confirm = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_payment(billing_day: int) -> date:
    """Return next occurrence of billing_day from today."""
    today = date.today()
    # Try this month
    try:
        candidate = today.replace(day=billing_day)
    except ValueError:
        # billing_day > days in month
        last = calendar.monthrange(today.year, today.month)[1]
        candidate = today.replace(day=last)
    if candidate <= today:
        # Next month
        if today.month == 12:
            candidate = date(today.year + 1, 1, 1)
        else:
            candidate = date(today.year, today.month + 1, 1)
        try:
            candidate = candidate.replace(day=billing_day)
        except ValueError:
            last = calendar.monthrange(candidate.year, candidate.month)[1]
            candidate = candidate.replace(day=last)
    return candidate


def _days_until(d: date | None) -> str:
    if d is None:
        return "?"
    delta = (d - date.today()).days
    if delta < 0:
        return f"просрочено ({abs(delta)} дн.)"
    if delta == 0:
        return "сегодня ⚠️"
    if delta <= 3:
        return f"{delta} дн. ⚠️"
    return f"{delta} дн."


def _server_summary(s: InfrastructureServer) -> str:
    if s.billing_type == "fixed":
        billing_info = (
            f"💰 {s.monthly_cost_rub} ₽/мес, "
            f"день оплаты: {s.billing_day}\n"
            f"📅 Следующая оплата: {s.next_payment_date} ({_days_until(s.next_payment_date)})"
        )
    else:
        rate = s.estimated_hourly_rate_rub or "?"
        billing_info = f"⏱ Почасовая ≈ {rate} ₽/ч"
    return (
        f"🖥 <b>{s.name}</b>\n"
        f"🏢 {s.provider or '—'} | 📍 {s.location or '—'}\n"
        f"{billing_info}\n"
        f"🔔 Напомнить за {s.remind_days_before} дн.\n"
        f"{'📝 ' + s.notes if s.notes else ''}"
    ).strip()


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _billing_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Фиксированная (ежемесячно)", callback_data="srv_type_fixed")],
        [InlineKeyboardButton(text="⏱ Почасовая / динамическая", callback_data="srv_type_hourly")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_submenu_system")],
    ])


def _skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="srv_skip")],
    ])


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="srv_save"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="srv_cancel"),
        ],
    ])


def _server_keyboard(server_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"srv_deact_{server_id}")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="admin_servers")],
    ])


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_submenu_system")],
    ])


# ---------------------------------------------------------------------------
# Handlers — list
# ---------------------------------------------------------------------------

@admin_required
@error_handler
async def show_servers(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    result = await db.execute(
        select(InfrastructureServer)
        .where(InfrastructureServer.is_active.is_(True))
        .order_by(InfrastructureServer.next_payment_date.asc().nullsfirst())
    )
    servers = list(result.scalars().all())

    if not servers:
        await callback.message.edit_text(
            "🖥 <b>Серверы инфраструктуры</b>\n\nСерверов пока нет.",
            parse_mode="HTML",
            reply_markup=_back_keyboard(),
        )
        await callback.answer()
        return

    lines = ["🖥 <b>Серверы инфраструктуры</b>\n"]
    total_monthly = Decimal(0)
    for s in servers:
        status = ""
        if s.billing_type == "fixed" and s.next_payment_date:
            days = (s.next_payment_date - date.today()).days
            if days <= s.remind_days_before:
                status = " ⚠️"
            cost_str = f"{s.monthly_cost_rub} ₽/мес"
            total_monthly += Decimal(str(s.monthly_cost_rub or 0))
        else:
            cost_str = f"≈ {s.estimated_hourly_rate_rub} ₽/ч"

        lines.append(
            f"• <b>{s.name}</b>{status} — {cost_str}\n"
            f"  {s.provider or ''} {s.location or ''} | "
            f"{'до ' + str(s.next_payment_date) if s.next_payment_date else 'почасовая'}"
        )

    if total_monthly > 0:
        lines.append(f"\n💸 <b>Итого фиксированных: {total_monthly} ₽/мес</b>")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        *[
            [InlineKeyboardButton(
                text=f"{'⚠️ ' if s.billing_type == 'fixed' and s.next_payment_date and (s.next_payment_date - date.today()).days <= s.remind_days_before else ''}{s.name}",
                callback_data=f"srv_view_{s.id}",
            )]
            for s in servers
        ],
        [InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_submenu_system")],
    ])

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=keyboard,
    )
    await callback.answer()


@admin_required
@error_handler
async def view_server(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    server_id = int(callback.data.split("_")[-1])
    server = await db.get(InfrastructureServer, server_id)
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await callback.message.edit_text(
        _server_summary(server), parse_mode="HTML",
        reply_markup=_server_keyboard(server_id),
    )
    await callback.answer()


@admin_required
@error_handler
async def deactivate_server(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession
) -> None:
    server_id = int(callback.data.split("_")[-1])
    server = await db.get(InfrastructureServer, server_id)
    if server:
        server.is_active = False
        await db.commit()
    await callback.message.edit_text("✅ Сервер деактивирован.", reply_markup=_back_keyboard())
    await callback.answer()


# ---------------------------------------------------------------------------
# Handlers — add server FSM
# ---------------------------------------------------------------------------

@admin_required
@error_handler
async def start_add_server(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await state.set_state(ServerStates.billing_type)
    await callback.message.edit_text(
        "🖥 <b>Добавить сервер</b>\n\nВыберите тип биллинга:",
        parse_mode="HTML",
        reply_markup=_billing_type_keyboard(),
    )
    await callback.answer()


@admin_required
@error_handler
async def choose_billing_type(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    btype = "fixed" if callback.data == "srv_type_fixed" else "hourly"
    await state.update_data(billing_type=btype)
    await state.set_state(ServerStates.name)
    await callback.message.edit_text(
        f"Тип: <b>{'Фиксированная' if btype == 'fixed' else 'Почасовая'}</b>\n\n"
        "Введите <b>название сервера</b> (например: Aeza Amsterdam #1):",
        parse_mode="HTML",
    )
    await callback.answer()


@admin_required
@error_handler
async def enter_name(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(ServerStates.provider)
    await message.answer(
        "Введите <b>провайдера</b> (Aeza, Hetzner, Selectel…) или пропустите:",
        parse_mode="HTML", reply_markup=_skip_keyboard(),
    )


@admin_required
@error_handler
async def enter_provider(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(provider=message.text.strip())
    await state.set_state(ServerStates.location)
    await message.answer(
        "Введите <b>локацию</b> (Amsterdam NL, Frankfurt DE…) или пропустите:",
        parse_mode="HTML", reply_markup=_skip_keyboard(),
    )


@admin_required
@error_handler
async def enter_location(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(location=message.text.strip())
    data = await state.get_data()
    if data["billing_type"] == "fixed":
        await state.set_state(ServerStates.monthly_cost)
        await message.answer("Введите <b>стоимость в месяц</b> (₽):", parse_mode="HTML")
    else:
        await state.set_state(ServerStates.hourly_rate)
        await message.answer(
            "Введите <b>примерную ставку ₽/час</b> для прогноза (или пропустите):",
            parse_mode="HTML", reply_markup=_skip_keyboard(),
        )


@admin_required
@error_handler
async def enter_monthly_cost(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    try:
        cost = Decimal(message.text.strip().replace(",", "."))
        if cost <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("❌ Введите положительное число, например <code>1500</code>", parse_mode="HTML")
        return
    await state.update_data(monthly_cost=str(cost))
    await state.set_state(ServerStates.billing_day)
    await message.answer(
        "Введите <b>день месяца</b> для оплаты (1–28):",
        parse_mode="HTML",
    )


@admin_required
@error_handler
async def enter_billing_day(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    try:
        day = int(message.text.strip())
        if not 1 <= day <= 28:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 28")
        return
    await state.update_data(billing_day=day)
    await _ask_remind_days(message, state)


@admin_required
@error_handler
async def enter_hourly_rate(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    try:
        rate = Decimal(message.text.strip().replace(",", "."))
    except InvalidOperation:
        await message.answer("❌ Введите число")
        return
    await state.update_data(hourly_rate=str(rate))
    await _ask_remind_days(message, state)


@admin_required
@error_handler
async def skip_field(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    current = await state.get_state()
    await callback.answer()
    data = await state.get_data()

    if current == ServerStates.provider:
        await state.update_data(provider=None)
        await state.set_state(ServerStates.location)
        await callback.message.edit_text(
            "Введите <b>локацию</b> или пропустите:", parse_mode="HTML",
            reply_markup=_skip_keyboard(),
        )
    elif current == ServerStates.location:
        await state.update_data(location=None)
        if data.get("billing_type") == "fixed":
            await state.set_state(ServerStates.monthly_cost)
            await callback.message.edit_text("Введите <b>стоимость в месяц</b> (₽):", parse_mode="HTML")
        else:
            await state.set_state(ServerStates.hourly_rate)
            await callback.message.edit_text(
                "Введите <b>ставку ₽/час</b> или пропустите:", parse_mode="HTML",
                reply_markup=_skip_keyboard(),
            )
    elif current == ServerStates.hourly_rate:
        await state.update_data(hourly_rate=None)
        await _ask_remind_days(callback.message, state)
    elif current == ServerStates.notes:
        await state.update_data(notes=None)
        await _show_server_confirm(callback.message, state)


async def _ask_remind_days(msg: types.Message, state: FSMContext) -> None:
    await state.set_state(ServerStates.remind_days)
    await msg.answer(
        "За сколько дней напоминать об оплате? (по умолчанию 3, пропустите для значения по умолчанию):",
        reply_markup=_skip_keyboard(),
    )


@admin_required
@error_handler
async def enter_remind_days(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число ≥ 1")
        return
    await state.update_data(remind_days=days)
    await state.set_state(ServerStates.notes)
    await message.answer("Добавьте <b>заметку</b> (необязательно):", parse_mode="HTML",
                         reply_markup=_skip_keyboard())


@admin_required
@error_handler
async def skip_remind_days(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    current = await state.get_state()
    await callback.answer()
    if current == ServerStates.remind_days:
        await state.update_data(remind_days=3)
        await state.set_state(ServerStates.notes)
        await callback.message.edit_text(
            "Добавьте <b>заметку</b> (необязательно):", parse_mode="HTML",
            reply_markup=_skip_keyboard(),
        )


@admin_required
@error_handler
async def enter_notes(
    message: types.Message, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.update_data(notes=message.text.strip())
    await _show_server_confirm(message, state)


async def _show_server_confirm(msg: types.Message, state: FSMContext) -> None:
    await state.set_state(ServerStates.confirm)
    data = await state.get_data()
    btype = data.get("billing_type", "fixed")
    if btype == "fixed":
        billing_line = f"💰 {data.get('monthly_cost')} ₽/мес, день {data.get('billing_day')}"
    else:
        billing_line = f"⏱ ≈ {data.get('hourly_rate') or '—'} ₽/ч"
    text = (
        f"<b>Проверьте данные:</b>\n\n"
        f"Название: {data.get('name')}\n"
        f"Провайдер: {data.get('provider') or '—'}\n"
        f"Локация: {data.get('location') or '—'}\n"
        f"Биллинг: {billing_line}\n"
        f"Напоминание: за {data.get('remind_days', 3)} дн.\n"
        f"Заметка: {data.get('notes') or '—'}"
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=_confirm_keyboard())


@admin_required
@error_handler
async def save_server(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    await state.clear()

    btype = data.get("billing_type", "fixed")
    billing_day = data.get("billing_day")
    next_pay = _next_payment(int(billing_day)) if billing_day and btype == "fixed" else None

    server = InfrastructureServer(
        name=data["name"],
        provider=data.get("provider"),
        location=data.get("location"),
        billing_type=btype,
        monthly_cost_rub=Decimal(data["monthly_cost"]) if data.get("monthly_cost") else None,
        billing_day=int(billing_day) if billing_day else None,
        next_payment_date=next_pay,
        estimated_hourly_rate_rub=(
            Decimal(data["hourly_rate"]) if data.get("hourly_rate") else None
        ),
        remind_days_before=int(data.get("remind_days", 3)),
        notes=data.get("notes"),
    )
    db.add(server)
    await db.commit()

    logger.info("Сервер добавлен", name=data["name"], admin_id=db_user.telegram_id)
    await callback.message.edit_text(
        f"✅ Сервер <b>{data['name']}</b> добавлен.",
        parse_mode="HTML",
        reply_markup=_back_keyboard(),
    )
    await callback.answer()


@admin_required
@error_handler
async def cancel_server(
    callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Отменено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_submenu_system")
        ]]),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_handlers(dp: Dispatcher) -> None:
    dp.callback_query.register(show_servers, F.data == "admin_servers")
    dp.callback_query.register(view_server, F.data.startswith("srv_view_"))
    dp.callback_query.register(deactivate_server, F.data.startswith("srv_deact_"))
    dp.callback_query.register(start_add_server, F.data == "admin_add_server")
    dp.callback_query.register(choose_billing_type, F.data.in_({"srv_type_fixed", "srv_type_hourly"}), ServerStates.billing_type)
    dp.message.register(enter_name, ServerStates.name)
    dp.message.register(enter_provider, ServerStates.provider)
    dp.message.register(enter_location, ServerStates.location)
    dp.message.register(enter_monthly_cost, ServerStates.monthly_cost)
    dp.message.register(enter_billing_day, ServerStates.billing_day)
    dp.message.register(enter_hourly_rate, ServerStates.hourly_rate)
    dp.message.register(enter_remind_days, ServerStates.remind_days)
    dp.message.register(enter_notes, ServerStates.notes)
    dp.callback_query.register(skip_field, F.data == "srv_skip")
    dp.callback_query.register(skip_remind_days, F.data == "srv_skip", ServerStates.remind_days)
    dp.callback_query.register(save_server, F.data == "srv_save", ServerStates.confirm)
    dp.callback_query.register(cancel_server, F.data == "srv_cancel")
