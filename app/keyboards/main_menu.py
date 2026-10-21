"""The bot's main menu, defined in one place.

The layout used to come from three competing sources: the cabinet's
``CABINET_MENU_LAYOUT`` and button styles stored in the database, the
``MENU_LAYOUT_ENABLED`` constructor, and a classic builder that put up to
fourteen buttons in pairs. In cabinet mode most buttons also opened the web
cabinet instead of the bot's own screens. The menu is now fixed here and does
not read any of that configuration; the cabinet is reachable through its own
"Личный кабинет" button.

The menu has four rows. The first button is always the one action that matters
most for the user's current state, so the state decides the rows:

========  ==========================  ==========================  ==========================
Row       NEW (no subscription)       TRIAL / ACTIVE              RENEW (expiring or ended)
========  ==========================  ==========================  ==========================
1         Попробовать / Купить        Подключиться                Продлить
2         Купить · Баланс             Моя подписка (1) · Баланс   Подключиться (2) · Баланс
3         Пригласить · Поддержка      Пригласить · Поддержка      Моя подписка · Поддержка
4         Кабинет · Инфо              Кабинет · Инфо              Пригласить · Инфо
5         —                           —                           Кабинет
========  ==========================  ==========================  ==========================

(1) "Купить подписку" while on a trial. (2) Only while access still works.

A started checkout ("Продолжить оформление") goes above row 1. Only the first
coloured button keeps its colour; see the colour rules in
:mod:`app.keyboards.icons`.

Language, promo code, rules, FAQ and contests live in the "Инфо" section.
Buttons that are switched off (referrals, support, cabinet URL) simply drop
out of their row; the rows themselves stay put so that banners made for each
section keep matching.
"""

from enum import StrEnum

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import NoInspectionAvailable

from app.config import settings
from app.keyboards.icons import STYLE_PAY, STYLE_USE, icon_button
from app.localization.loader import DEFAULT_LANGUAGE
from app.localization.texts import get_texts
from app.utils.subscription_utils import get_display_subscription_link


# A paid subscription with this many days or fewer left counts as "renew".
RENEW_WARNING_DAYS = 3


class MenuState(StrEnum):
    NEW = 'new'
    TRIAL = 'trial'
    ACTIVE = 'active'
    RENEW = 'renew'


def _loaded_tariff(subscription):
    """The subscription's tariff if it is already loaded, without a lazy load.

    A lazy load from an async session raises, and the menu must render even
    when the caller did not eager-load ``Subscription.tariff``.
    """
    try:
        if 'tariff' in sa_inspect(subscription).unloaded:
            return None
    except NoInspectionAvailable:
        pass
    return getattr(subscription, 'tariff', None)


def resolve_menu_state(subscription) -> MenuState:
    if subscription is None:
        return MenuState.NEW

    status = (getattr(subscription, 'actual_status', '') or '').lower()
    if status == 'pending':
        return MenuState.NEW
    if status not in ('active', 'trial'):
        return MenuState.RENEW

    if getattr(subscription, 'is_trial', False):
        return MenuState.TRIAL

    tariff = _loaded_tariff(subscription)
    if tariff is not None and getattr(tariff, 'is_daily', False):
        # Daily tariffs charge themselves every day; there is nothing to renew.
        return MenuState.ACTIVE

    days_left = getattr(subscription, 'days_left', None)
    if days_left is not None and days_left <= RENEW_WARNING_DAYS:
        return MenuState.RENEW
    return MenuState.ACTIVE


def is_trial_available(subscription, *, has_had_paid_subscription: bool, auth_type: str | None) -> bool:
    if has_had_paid_subscription or settings.is_trial_disabled_for_user(auth_type):
        return False
    return resolve_menu_state(subscription) == MenuState.NEW


def _is_support_enabled() -> bool:
    try:
        from app.services.support_settings_service import SupportSettingsService

        return SupportSettingsService.is_support_menu_enabled()
    except Exception:
        return settings.SUPPORT_MENU_ENABLED


def _connect_button(texts, subscription) -> InlineKeyboardButton:
    """ "Подключиться", honouring ``CONNECT_BUTTON_MODE`` like the subscription screen does."""
    label = texts.t('MAIN_MENU_BTN_CONNECT', 'Подключиться')
    fallback = icon_button('connect', label, callback_data='subscription_connect', style=STYLE_USE)

    mode = settings.CONNECT_BUTTON_MODE
    link = get_display_subscription_link(subscription)

    if mode == 'miniapp_subscription' and link:
        return icon_button('connect', label, web_app_url=link, style=STYLE_USE)
    if mode == 'miniapp_custom' and settings.MINIAPP_CUSTOM_URL:
        return icon_button('connect', label, web_app_url=settings.MINIAPP_CUSTOM_URL, style=STYLE_USE)
    if mode == 'link' and link:
        return icon_button('connect', label, url=link, style=STYLE_USE)
    if mode == 'happ_cryptolink' and link:
        callback = 'subscription_connect' if settings.is_multi_tariff_enabled() else 'open_subscription_link'
        return icon_button('connect', label, callback_data=callback, style=STYLE_USE)
    return fallback


def build_main_menu_keyboard(
    language: str = DEFAULT_LANGUAGE,
    *,
    subscription=None,
    balance_kopeks: int = 0,
    has_had_paid_subscription: bool = False,
    auth_type: str | None = None,
    is_admin: bool = False,
    is_moderator: bool = False,
    show_resume_checkout: bool = False,
    has_saved_cart: bool = False,
    custom_buttons: list[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
    texts = get_texts(language)
    state = resolve_menu_state(subscription)

    def t(key: str, default: str) -> str:
        return texts.t(key, default)

    buy = icon_button('buy', t('MAIN_MENU_BTN_BUY', 'Купить подписку'), callback_data='menu_buy')
    balance = icon_button(
        'balance',
        t('MAIN_MENU_BTN_BALANCE', 'Баланс: {balance}').format(balance=texts.format_price(balance_kopeks or 0)),
        callback_data='menu_balance',
    )
    my_subscription = icon_button(
        'subscription',
        t('MAIN_MENU_BTN_SUBSCRIPTION', 'Моя подписка'),
        callback_data='menu_subscription',
    )
    referral = (
        icon_button('referral', t('MAIN_MENU_BTN_REFERRAL', 'Пригласить друга'), callback_data='menu_referrals')
        if settings.is_referral_program_enabled()
        else None
    )
    support = (
        icon_button('support', t('MAIN_MENU_BTN_SUPPORT', 'Поддержка'), callback_data='menu_support')
        if _is_support_enabled()
        else None
    )
    cabinet_url = settings.get_cabinet_home_url()
    cabinet = (
        icon_button('cabinet', t('MAIN_MENU_BTN_CABINET', 'Личный кабинет'), url=cabinet_url) if cabinet_url else None
    )
    info = icon_button('info', t('MAIN_MENU_BTN_INFO', 'Инфо'), callback_data='menu_info')

    rows: list[list[InlineKeyboardButton | None]] = []

    if state == MenuState.NEW:
        if is_trial_available(subscription, has_had_paid_subscription=has_had_paid_subscription, auth_type=auth_type):
            rows.append(
                [
                    icon_button(
                        'trial',
                        t('MAIN_MENU_BTN_TRIAL', 'Попробовать бесплатно'),
                        callback_data='menu_trial',
                        style=STYLE_PAY,
                    )
                ]
            )
            rows.append([buy, balance])
        else:
            rows.append(
                [
                    icon_button(
                        'buy', t('MAIN_MENU_BTN_BUY', 'Купить подписку'), callback_data='menu_buy', style=STYLE_PAY
                    )
                ]
            )
            rows.append([balance])
        rows.append([referral, support])
        rows.append([cabinet, info])

    elif state in (MenuState.TRIAL, MenuState.ACTIVE):
        rows.append([_connect_button(texts, subscription)])
        rows.append([buy if state == MenuState.TRIAL else my_subscription, balance])
        rows.append([referral, support])
        rows.append([cabinet, info])

    else:  # MenuState.RENEW
        rows.append(
            [
                icon_button(
                    'renew',
                    t('MAIN_MENU_BTN_RENEW', 'Продлить подписку'),
                    callback_data='subscription_extend',
                    style=STYLE_PAY,
                )
            ]
        )
        still_works = getattr(subscription, 'is_active', False)
        rows.append([_connect_button(texts, subscription) if still_works else None, balance])
        rows.append([my_subscription, support])
        rows.append([referral, info])
        rows.append([cabinet])

    if show_resume_checkout or has_saved_cart:
        # A purchase the user already started is the most likely next step,
        # so it goes on top and takes the screen's accent colour.
        resume_callback = 'return_to_saved_cart' if has_saved_cart else 'subscription_resume_checkout'
        rows.insert(
            0,
            [
                icon_button(
                    'checkout',
                    t('MAIN_MENU_BTN_CHECKOUT', 'Продолжить оформление'),
                    callback_data=resume_callback,
                    style=STYLE_PAY,
                )
            ],
        )

    # Extra links an admin added through the bot's own admin panel.
    for button in custom_buttons or []:
        if isinstance(button, InlineKeyboardButton):
            rows.append([button])

    if is_admin:
        rows.append([icon_button('admin', t('MAIN_MENU_BTN_ADMIN', 'Админ-панель'), callback_data='admin_panel')])
    elif is_moderator:
        rows.append(
            [icon_button('moderation', t('MAIN_MENU_BTN_MODERATION', 'Модерация'), callback_data='moderator_panel')]
        )

    keyboard = [[button for button in row if button is not None] for row in rows]
    return InlineKeyboardMarkup(inline_keyboard=keep_single_accent([row for row in keyboard if row]))


def keep_single_accent(rows: list[list[InlineKeyboardButton]]) -> list[list[InlineKeyboardButton]]:
    """Leave the colour only on the first coloured button of the screen.

    One accent per screen is the rule of the colour system (see
    :mod:`app.keyboards.icons`): a second coloured button competes with the
    first and both stop reading as "the next step".
    """
    seen_accent = False
    result = []
    for row in rows:
        new_row = []
        for button in row:
            if button.style:
                if seen_accent:
                    button = button.model_copy(update={'style': None})
                seen_accent = True
            new_row.append(button)
        result.append(new_row)
    return result


__all__ = [
    'RENEW_WARNING_DAYS',
    'MenuState',
    'build_main_menu_keyboard',
    'is_trial_available',
    'keep_single_accent',
    'resolve_menu_state',
]
