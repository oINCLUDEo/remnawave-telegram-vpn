"""Shared navigation buttons.

Back and close exist on nearly every screen in the bot, and until now each of
the ~170 call sites spelled its own label inline. Four different arrows were in
use for "Назад" (⬅️ 122×, ◀️ 22×, 🔙 8×, ↩️ 1×) and two crosses for "Закрыть",
and because the strings were hardcoded Russian they never translated for the
other four locales the bot ships.

Everything funnels through here instead, so the icon, the wording and the
translation are decided in one place.
"""

from aiogram.types import InlineKeyboardButton

from app.localization.texts import get_texts
from app.utils.miniapp_buttons import strip_leading_emoji_if_custom_icon


# Telegram custom emoji shown as the button's own icon (aiogram >= 3.25,
# InlineKeyboardButton.icon_custom_emoji_id). The label deliberately carries no
# Unicode emoji of its own — Telegram draws the custom icon beside it, and a
# leading ⬅️ would render a second arrow next to the first.
BACK_ICON_CUSTOM_EMOJI_ID = '5258236805890710909'
# ✖️, not ❌: in message text ❌ means something broke, so dismissing must look different.
CLOSE_ICON_CUSTOM_EMOJI_ID = '5226660202035554522'


def back_button(
    callback_data: str = 'back_to_menu',
    *,
    language: str = 'ru',
    text: str | None = None,
) -> InlineKeyboardButton:
    """The standard "back one level" button.

    Pass *text* only for the handful of places that name their destination
    ("Назад к тарифу"); the icon stays the same either way. Pagination arrows
    are a different control and must not use this — they move through a list
    rather than leaving the screen.
    """
    texts = get_texts(language)
    label = text or texts.t('BACK_BUTTON', 'Назад')
    return InlineKeyboardButton(
        text=strip_leading_emoji_if_custom_icon(label, BACK_ICON_CUSTOM_EMOJI_ID),
        callback_data=callback_data,
        icon_custom_emoji_id=BACK_ICON_CUSTOM_EMOJI_ID,
    )


def close_button(
    callback_data: str = 'close_message',
    *,
    language: str = 'ru',
    text: str | None = None,
) -> InlineKeyboardButton:
    """The standard "dismiss this message" button."""
    texts = get_texts(language)
    label = text or texts.t('CLOSE_BUTTON', 'Закрыть')
    return InlineKeyboardButton(
        text=strip_leading_emoji_if_custom_icon(label, CLOSE_ICON_CUSTOM_EMOJI_ID),
        callback_data=callback_data,
        icon_custom_emoji_id=CLOSE_ICON_CUSTOM_EMOJI_ID,
    )
