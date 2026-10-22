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

from app.keyboards.icons import ICONS
from app.localization.texts import get_texts
from app.utils.miniapp_buttons import strip_leading_emoji_if_custom_icon


# The icons come from app.keyboards.icons.ICONS, read when a button is built
# (drop_unknown_icons may switch one off at startup). Telegram draws the custom
# emoji as the button's own icon (aiogram >= 3.25, icon_custom_emoji_id), so
# the label carries no Unicode emoji: a leading ⬅️ would make a second arrow.
# Close wears the line cross: on a button it is never the colour ❌ that means
# something broke.


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
    icon_id = ICONS['back'].custom_emoji_id
    return InlineKeyboardButton(
        text=strip_leading_emoji_if_custom_icon(label, icon_id),
        callback_data=callback_data,
        icon_custom_emoji_id=icon_id,
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
    icon_id = ICONS['cross'].custom_emoji_id
    return InlineKeyboardButton(
        text=strip_leading_emoji_if_custom_icon(label, icon_id),
        callback_data=callback_data,
        icon_custom_emoji_id=icon_id,
    )
