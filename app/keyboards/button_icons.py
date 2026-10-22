"""Monochrome icons for every inline button, wherever it is built.

The bot builds buttons in hundreds of places, and most labels start with a
plain emoji («🔄 Обновить», «📊 Статистика»). Instead of changing each one, the
bot's session runs :class:`ButtonIconsMiddleware` on every request: a button
whose label starts with an emoji from :data:`BUTTON_EMOJI` gets that icon from
:data:`app.keyboards.icons.ICONS` as its own icon (``icon_custom_emoji_id``),
and the emoji is taken out of the label. So the base stays monochrome, in one
style, and the colour accents are the ones in ``ICONS``.

Left as they are:

- buttons that already have an icon (``icon_button``);
- emoji not in :data:`BUTTON_EMOJI`: the statuses (✅ ❌ 🟢 🔴 🚫), flags,
  platform logos and the rest;
- a label that is only an emoji, such as a pagination arrow: a button needs text;
- reply keyboards: their text is sent back as a message, and handlers match it;
- messages outside private chats: Telegram allows custom emoji on buttons in
  private chats and groups but not in channels, and a group's id cannot be told
  from a channel's, so only private chats get the icons.
"""

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.icons import ICONS


# The plain emoji at the start of a label → the ICONS key whose icon replaces it.
# Written without the variation selector (U+FE0F); labels match with or without it.
BUTTON_EMOJI: dict[str, str] = {
    '⬅': 'back',
    '◀': 'back',
    '🔙': 'back',
    '↩': 'back',
    '🏠': 'home',
    '🔄': 'refresh',
    '🔁': 'refresh',
    '♻': 'refresh',
    '📊': 'stats',
    '📋': 'list',
    '✏': 'edit',
    '📝': 'edit',
    '➕': 'add',
    '🗑': 'delete',
    '🔍': 'search',
    '👁': 'view',
    '👀': 'view',
    '🔗': 'link',
    '📤': 'share',
    '⬇': 'download',
    '📥': 'download',
    '✉': 'send',
    '📨': 'send',
    '📬': 'send',
    '💬': 'chat',
    '📢': 'announce',
    '📣': 'announce',
    '📄': 'document',
    '🧾': 'document',
    '❓': 'guide',
    '🔒': 'lock',
    '🔐': 'lock',
    '🛡': 'lock',
    '📅': 'calendar',
    '📆': 'calendar',
    '🗓': 'calendar',
    '⏳': 'time',
    '⌛': 'time',
    '⏰': 'time',
    '⏱': 'time',
    '🕒': 'time',
    '👥': 'people',
    '🤝': 'people',
    '👤': 'profile',
    '🪙': 'coin',
    '⚙': 'settings',
    '🔧': 'settings',
    '🛠': 'settings',
    '📱': 'devices',
    '📈': 'traffic',
    '💰': 'balance',
    'ℹ': 'info',
    '🆘': 'support',
    '🛟': 'support',
    '🎫': 'promocode',
    # The product and the warning keep their colour icons.
    '🪐': 'connect',
    '💎': 'subscription',
    '🎁': 'trial',
    '💳': 'payment',
    '📦': 'tariff',
    '⚠': 'warning',
}

_VARIATION_SELECTOR = '️'

# (label prefix, custom emoji id), longest prefix first, so «⚙️» is tried before «⚙».
_PREFIXES: list[tuple[str, str]] = sorted(
    (
        (prefix, ICONS[key].custom_emoji_id)
        for emoji, key in BUTTON_EMOJI.items()
        for prefix in (emoji + _VARIATION_SELECTOR, emoji)
        if ICONS[key].custom_emoji_id
    ),
    key=lambda item: len(item[0]),
    reverse=True,
)


def _label_icon(text: str) -> tuple[str, str] | None:
    """The icon id and the label without its leading emoji, or None to leave the label as it is."""
    for prefix, emoji_id in _PREFIXES:
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix) :]
        if not rest[:1].isspace() or not rest.strip():
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
