"""A picture per bot section, with the logo as the fallback.

Every screen used to show the same logo (``ENABLE_LOGO_MODE``). Now each
section has a banner key, and the picture sent with a screen is
``assets/banners/<key>.png`` (or ``.jpg``/``.jpeg``/``.webp``) when that file
exists, otherwise the logo as before. Adding a banner is dropping a file into
the folder; no code changes.

The key is picked from the update itself: the button the user pressed
(``callback_data``) or the command they sent. :class:`BannerMiddleware`
stores it in a context variable for the duration of the update, and the
photo helpers in :mod:`app.utils.message_patch` read it when they choose the
picture. Screens reached in other ways (notifications, payment webhooks) keep
the logo.

Keys and the screens they cover:

==================  ==========================================================
main                главное меню (/start, «Назад»)
subscription        «Моя подписка», устройства, настройки подписки
buy                 покупка: список тарифов, тариф, период
renew               продление
trial               пробный период
connect             подключение и инструкции
balance             баланс и история
payment             пополнение и выбор способа оплаты
referral            «Пригласить друга»
support             поддержка и тикеты
info                «Инфо», личный кабинет, правила, FAQ, язык, промокод
==================  ==========================================================
"""

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


BANNERS_DIR = Path(__file__).resolve().parents[2] / 'assets' / 'banners'
_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')

BANNER_KEYS = (
    'main',
    'subscription',
    'buy',
    'renew',
    'trial',
    'connect',
    'balance',
    'payment',
    'referral',
    'support',
    'info',
)

# Exact callback_data → banner key.
_CALLBACK_BANNERS: dict[str, str] = {
    'back_to_menu': 'main',
    'menu_subscription': 'subscription',
    'my_subscriptions': 'subscription',
    'subscription_settings': 'subscription',
    'subscription_manage_devices': 'subscription',
    'menu_buy': 'buy',
    'subscription_upgrade': 'buy',
    'subscription_purchase': 'buy',
    'tariff_list': 'buy',
    'buy_subscription_tariffs': 'buy',
    'subscription_extend': 'renew',
    'menu_trial': 'trial',
    'trial_activate': 'trial',
    'menu_balance': 'balance',
    'balance_history': 'balance',
    'balance_topup': 'payment',
    'menu_referrals': 'referral',
    'menu_support': 'support',
    'my_tickets': 'support',
    'create_ticket': 'support',
    'menu_info': 'info',
    'menu_rules': 'info',
    'menu_faq': 'info',
    'menu_privacy_policy': 'info',
    'menu_public_offer': 'info',
    'menu_language': 'info',
    'menu_promocode': 'info',
}

# callback_data prefix → banner key, checked in order after the exact map.
_CALLBACK_PREFIX_BANNERS: tuple[tuple[str, str], ...] = (
    ('subscription_connect', 'connect'),
    ('device_guide_', 'connect'),
    ('app_list_', 'connect'),
    ('tariff_extend:', 'renew'),
    ('tariff_ext_confirm:', 'renew'),
    ('extend_period_', 'renew'),
    ('se:', 'renew'),
    ('tariff_', 'buy'),
    ('period_', 'buy'),
    ('sm:', 'subscription'),
    ('balance_history_page_', 'balance'),
    ('topup_', 'payment'),
    ('balance_topup_', 'payment'),
    ('referral_', 'referral'),
    ('menu_faq_page:', 'info'),
    ('menu_privacy_policy:', 'info'),
    ('menu_public_offer:', 'info'),
)

_current_banner: ContextVar[str | None] = ContextVar('current_banner', default=None)


def banner_key_for_callback(data: str | None) -> str | None:
    if not data:
        return None
    if data in _CALLBACK_BANNERS:
        return _CALLBACK_BANNERS[data]
    for prefix, key in _CALLBACK_PREFIX_BANNERS:
        if data.startswith(prefix):
            return key
    return None


def banner_key_for_message(text: str | None) -> str | None:
    if text and text.split(maxsplit=1)[0].split('@', 1)[0] == '/start':
        return 'main'
    return None


def banner_path(key: str | None) -> Path | None:
    """The banner file for *key*, or ``None`` when the designer has not added one yet."""
    if not key:
        return None
    for extension in _EXTENSIONS:
        candidate = BANNERS_DIR / f'{key}{extension}'
        if candidate.is_file():
            return candidate
    return None


def current_banner_key() -> str | None:
    return _current_banner.get()


def set_current_banner(key: str | None):
    """Override the banner for the rest of this update; returns a token for ``reset``."""
    return _current_banner.set(key)


class BannerMiddleware(BaseMiddleware):
    """Remembers which section the current update opens, for the photo helpers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        key = None
        if isinstance(event, CallbackQuery):
            key = banner_key_for_callback(event.data)
        elif isinstance(event, Message):
            key = banner_key_for_message(event.text)

        token = _current_banner.set(key)
        try:
            return await handler(event, data)
        finally:
            _current_banner.reset(token)
