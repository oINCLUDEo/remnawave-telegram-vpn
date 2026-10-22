"""The bot's icons in message texts, wherever the text is written.

Locales and code write plain emoji («💰 Баланс», «✅ Готово»). Plain emoji are
drawn by the user's phone, in colour and in its own style, so next to the
line icons on the buttons they looked scattered. The bot's session runs
:class:`TextIconsMiddleware` on every request: in an HTML text or caption,
each emoji from :data:`app.keyboards.icons.EMOJI_KEYS` becomes the matching
custom emoji from :data:`app.keyboards.icons.ICONS` (``<tg-emoji>``), so
texts and buttons share one monochrome set.

Statuses are the one place for colour, and a message gets one: the first
status emoji (✅ ❌ ⚠️ 🚫 and the like) is drawn in colour, the later ones as
line icons, so a list of ✅ stays calm. A colour icon already in the text
(``tg_emoji('warning')``) counts as that one. 🎉 is always in colour.

Left as they are:

- texts that are not HTML, and texts sent with entities;
- emoji inside ``<code>``, ``<pre>`` or an existing ``<tg-emoji>``, and emoji
  that are part of a longer sequence (joined with U+200D);
- emoji not in ``EMOJI_KEYS`` (flags, the coloured circles, digits);
- messages outside private chats, as for buttons (app/keyboards/button_icons.py).
"""

import re

from aiogram.client.default import Default
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

from app.keyboards.icons import ACCENT_KEYS, EMOJI_KEYS, ICONS, STATUS_ACCENTS


# Telegram draws a limited number of custom emoji per message; past this the emoji stay plain.
_MAX_ICONS = 50

_ZWJ = '\u200d'
# What may follow an emoji inside a longer one: the variation selector, a joiner,
# the keycap mark, a skin tone. «🧑‍💻» or «🤝🏻» must not lose a part.
_JOINERS = '\ufe0f\u200d\u20e3\U0001f3fb-\U0001f3ff'
_EMOJI_RE = re.compile(
    f'(?<!{_ZWJ})('
    + '|'.join(re.escape(emoji) for emoji in sorted(EMOJI_KEYS, key=len, reverse=True))
    + f')(\ufe0f?)(?![{_JOINERS}])'
)
_TAG_RE = re.compile(r'(<[^>]*>)')
_SKIP_TAG_RE = re.compile(r'<(/?)(code|pre|tg-emoji)\b', re.IGNORECASE)


def _accent_ids() -> set[str]:
    return {ICONS[key].custom_emoji_id for key in ACCENT_KEYS if ICONS[key].custom_emoji_id}


def with_text_icons(text: str) -> str:
    """*text* (HTML) with its plain emoji drawn as the bot's icons."""
    accent_used = any(f'emoji-id="{emoji_id}"' in text for emoji_id in _accent_ids())
    drawn = text.count('<tg-emoji')

    def replace(match: re.Match) -> str:
        nonlocal accent_used, drawn
        key = EMOJI_KEYS[match.group(1)]
        accent = STATUS_ACCENTS.get(key)
        if accent and not accent_used and ICONS[accent].custom_emoji_id:
            key = accent
        emoji_id = ICONS[key].custom_emoji_id
        if not emoji_id or drawn >= _MAX_ICONS:
            return match.group(0)
        if key in ACCENT_KEYS:
            accent_used = True
        drawn += 1
        return f'<tg-emoji emoji-id="{emoji_id}">{match.group(0)}</tg-emoji>'

    parts = _TAG_RE.split(text)
    skip_depth = 0
    for index, part in enumerate(parts):
        if index % 2:
            tag = _SKIP_TAG_RE.match(part)
            if tag:
                skip_depth = max(0, skip_depth + (-1 if tag.group(1) else 1))
        elif part and not skip_depth:
            parts[index] = _EMOJI_RE.sub(replace, part)
    return ''.join(parts)


def _is_html(bot, parse_mode) -> bool:
    if isinstance(parse_mode, Default):
        parse_mode = bot.default[parse_mode.name]
    return isinstance(parse_mode, str) and parse_mode.upper() == 'HTML'


class TextIconsMiddleware(BaseRequestMiddleware):
    """Applies :func:`with_text_icons` to the text or caption of every outgoing message."""

    async def __call__(self, make_request, bot, method):
        chat_id = getattr(method, 'chat_id', None)
        # A private chat's id is the user's id, always positive; groups and channels are negative.
        if isinstance(chat_id, int) and chat_id > 0:
            for field, entities_field in (('text', 'entities'), ('caption', 'caption_entities')):
                value = getattr(method, field, None)
                if (
                    isinstance(value, str)
                    and not getattr(method, entities_field, None)
                    and _is_html(bot, getattr(method, 'parse_mode', None))
                ):
                    setattr(method, field, with_text_icons(value))

            # edit_text in logo mode edits the photo's caption (app/utils/message_patch.py).
            media = getattr(method, 'media', None)
            caption = getattr(media, 'caption', None)
            if (
                isinstance(caption, str)
                and not getattr(media, 'caption_entities', None)
                and _is_html(bot, getattr(media, 'parse_mode', None))
            ):
                method.media = media.model_copy(update={'caption': with_text_icons(caption)})
        return await make_request(bot, method)
