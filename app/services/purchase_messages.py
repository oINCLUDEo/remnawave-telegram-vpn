"""Messages after a subscription is bought or renewed with money from the balance.

The purchase screen, the auto-purchase after a top-up and the renewal of an
expired subscription after a top-up all end with the same message: until
when the subscription works, where the money went, and «Подключиться».
"""

from __future__ import annotations

import html
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings
from app.keyboards.icons import tg_emoji
from app.localization.texts import get_texts
from app.utils.formatters import format_devices_count, format_human_date


# Telegram's 🎉 message effect. Only the first paid purchase gets it: the
# animation is the celebration, so the text needs no exclamation mark.
CELEBRATION_EFFECT_ID = '5046509860389126442'


def build_subscription_ready_message(
    user: Any,
    subscription: Any,
    *,
    renewed: bool,
    price_kopeks: int,
    topup_kopeks: int = 0,
    tariff_name: str | None = None,
    details: str | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """«💎 Подписка оформлена до 20 ноября» with where the money went and «Подключиться».

    After a top-up the second line explains the balance: «Баланс пополнен на
    179 ₽, за подписку списано 299 ₽». Otherwise it says what was charged and
    what is left. *details* is an optional quoted line about the tariff.
    """
    from app.keyboards.main_menu import connect_button

    language = getattr(user, 'language', None) or 'ru'
    texts = get_texts(language)
    fmt = settings.format_price

    tariff_label = ''
    if settings.is_multi_tariff_enabled() and tariff_name:
        tariff_label = f' «{html.escape(tariff_name)}»'
    if renewed:
        title = texts.t('SUBSCRIPTION_RENEWED_UNTIL', '{icon} <b>Подписка{tariff_label} продлена до {date}</b>')
    else:
        title = texts.t('SUBSCRIPTION_ACTIVE_UNTIL', '{icon} <b>Подписка{tariff_label} оформлена до {date}</b>')
    lines = [
        title.format(
            icon=tg_emoji('subscription'),
            tariff_label=tariff_label,
            date=format_human_date(subscription.end_date, language),
        )
    ]

    if topup_kopeks > 0:
        money = texts.t('SUBSCRIPTION_PAID_FROM_TOPUP', 'Баланс пополнен на {topup}, за подписку списано {price}.')
        money = money.format(topup=fmt(topup_kopeks), price=fmt(price_kopeks))
    else:
        money = texts.t('SUBSCRIPTION_PAID_FROM_BALANCE', 'Списано {price}, на балансе {balance}.')
        money = money.format(price=fmt(price_kopeks), balance=fmt(getattr(user, 'balance_kopeks', 0) or 0))

    if details:
        lines.append(f'<blockquote>{details}\n{money}</blockquote>')
    else:
        lines.append(money)

    sub_suffix = f':{subscription.id}' if settings.is_multi_tariff_enabled() else ''
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [connect_button(texts, subscription, sub_suffix=sub_suffix)],
            [InlineKeyboardButton(text=texts.t('MAIN_MENU_BUTTON', '🏠 Главное меню'), callback_data='back_to_menu')],
        ]
    )
    return '\n'.join(lines), keyboard


def subscription_details(language: str, tariff_name: str | None, device_limit: int, traffic_limit_gb: int) -> str:
    """«Стандарт · 3 устройства · безлимитный трафик» for the quoted line of the message.

    With several tariffs the title already names the tariff, so the line leaves it out.
    """
    texts = get_texts(language)
    parts = []
    if tariff_name and not settings.is_multi_tariff_enabled():
        parts.append(html.escape(tariff_name))
    if device_limit:
        parts.append(format_devices_count(device_limit, language))
    if traffic_limit_gb:
        parts.append(texts.t('PURCHASE_TRAFFIC_LIMITED', '{gb} ГБ трафика').format(gb=traffic_limit_gb))
    else:
        parts.append(texts.t('PURCHASE_TRAFFIC_UNLIMITED', 'безлимитный трафик'))
    return ' · '.join(parts)


def topup_note(language: str, topup_kopeks: int) -> str:
    """«Баланс пополнен на 300 ₽.» for the other messages that follow a top-up, or ''."""
    if topup_kopeks <= 0:
        return ''
    texts = get_texts(language)
    return texts.t('TOPUP_NOTE', 'Баланс пополнен на {amount}.').format(amount=settings.format_price(topup_kopeks))
