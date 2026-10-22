"""Monochrome icons for every inline button, wherever it is built.

The bot builds buttons in hundreds of places, and most labels start with a
plain emoji («🔄 Обновить», «📊 Статистика»). Instead of changing each one, the
bot's session runs :class:`ButtonIconsMiddleware` on every request: a button
whose label starts with an emoji from :data:`app.keyboards.icons.EMOJI_KEYS`
gets that icon from :data:`app.keyboards.icons.ICONS` as its own icon
(``icon_custom_emoji_id``), and the emoji is taken out of the label. Buttons
are always monochrome, statuses included (a ✅ toggle wears the line check):
a button's colour is its ``style``, not its icon.

Left as they are:

- buttons that already have an icon (``icon_button``);
- emoji not in ``EMOJI_KEYS``: flags, the coloured circles, digits and the rest;
- a label that is only an emoji, such as a pagination arrow: a button needs text;
- reply keyboards: their text is sent back as a message, and handlers match it;
- messages outside private chats: Telegram allows custom emoji on buttons in
  private chats and groups but not in channels, and a group's id cannot be told
  from a channel's, so only private chats get the icons.
"""

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.icons import ACCENT_KEYS, EMOJI_KEYS, ICONS


_VARIATION_SELECTOR = '\ufe0f'

# (label prefix, ICONS key), longest prefix first, so «⚙️» is tried before «⚙».
# Colour icons stay out: 🎉 on a button keeps its plain emoji.
_PREFIXES: list[tuple[str, str]] = sorted(
    (
        (prefix, key)
        for emoji, key in EMOJI_KEYS.items()
        if key not in ACCENT_KEYS
        for prefix in (emoji + _VARIATION_SELECTOR, emoji)
    ),
    key=lambda item: len(item[0]),
    reverse=True,
)


def _label_icon(text: str) -> tuple[str, str] | None:
    """The icon id and the label without its leading emoji, or None to leave the label as it is."""
    for prefix, key in _PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix) :]
        # The id is read here, not when the table is built: drop_unknown_icons may clear it at startup.
        emoji_id = ICONS[key].custom_emoji_id
        if not emoji_id or not rest[:1].isspace() or not rest.strip():
            return None
        return emoji_id, rest.strip()
    return None


def _with_icon(button: InlineKeyboardButton) -> InlineKeyboardButton:
    if button.icon_custom_emoji_id or not button.text:
        return button
    found = _label_icon(button.text)
    if found is None:
        return button
    emoji_id, text = found
    return button.model_copy(update={'text': text, 'icon_custom_emoji_id': emoji_id})


def with_button_icons(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """A copy of *markup* where labels that start with a known emoji wear its icon instead."""
    rows = []
    changed = False
    for row in markup.inline_keyboard:
        new_row = []
        for button in row:
            new_button = _with_icon(button)
            changed = changed or new_button is not button
            new_row.append(new_button)
        rows.append(new_row)
    return markup.model_copy(update={'inline_keyboard': rows}) if changed else markup


class ButtonIconsMiddleware(BaseRequestMiddleware):
    """Applies :func:`with_button_icons` to the inline keyboard of every outgoing request."""

    async def __call__(self, make_request, bot, method):
        markup = getattr(method, 'reply_markup', None)
        chat_id = getattr(method, 'chat_id', None)
        # A private chat's id is the user's id, always positive; groups and channels are negative.
        if isinstance(markup, InlineKeyboardMarkup) and isinstance(chat_id, int) and chat_id > 0:
            method.reply_markup = with_button_icons(markup)
        return await make_request(bot, method)
