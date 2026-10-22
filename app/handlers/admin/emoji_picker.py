"""/emoji: premium emoji ids for the bot's icons without looking them up one by one.

- ``/emoji https://t.me/addemoji/<pack>`` lists the whole pack and, for every
  icon in ``app.keyboards.icons.ICONS``, suggests the pack's emoji that are tied
  to the same plain emoji (or a related one);
- ``/emoji <id>`` does the same for the pack that emoji comes from;
- ``/emoji`` followed by premium emoji, or sent as a reply to a message with
  them, lists their ids.

Every id is in ``<code>``, so a tap copies it.
"""

import html
import re

import structlog
from aiogram import Dispatcher, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.keyboards.icons import ICONS, tg_emoji
from app.utils.decorators import admin_required, error_handler


logger = structlog.get_logger(__name__)

_PACK_LINK_RE = re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/(?:addemoji|addstickers)/(\w+)')
_PACK_NAME_RE = re.compile(r'^\w+$')
_EMOJI_ID_RE = re.compile(r'^\d{10,}$')

# Telegram draws a limited number of premium emoji per message; stay well below it.
_EMOJI_PER_MESSAGE = 45
_CHARS_PER_MESSAGE = 3500
_SUGGESTIONS_PER_ICON = 4

# Plain emoji that also suit an icon, besides the icon's own one.
_RELATED: dict[str, tuple[str, ...]] = {
    'connect': ('🌐', '🔌', '🚀', '🛰'),
    'subscription': ('👑', '⭐', '🛡'),
    'buy': ('🛍', '🛒', '👑'),
    'trial': ('🆓', '🎉'),
    'renew': ('🔄', '🔁', '⏰', '🕐', '⌛'),
    'autopay': ('🔄', '🔁', '⏰'),
    'balance': ('💵', '💸', '🪙', '👛'),
    'payment': ('💵', '💸', '🧾'),
    'referral': ('🤝', '👤', '🫂'),
    'support': ('💬', '🆘', '🛟', '📞'),
    'cabinet': ('🧑‍💻', '🏠'),
    'info': ('❓', '📖'),
    'tariff': ('📋', '🗂'),
    'devices': ('💻', '🖥', '⌚'),
    'settings': ('🔧', '🛠'),
    'traffic': ('📊', '📉', '📶'),
    'warning': ('❗', '‼️'),
    'expired': ('⛔', '❌'),
    'date': ('📅', '📆'),
    'language': ('🌐', '🗺'),
    'promocode': ('🏷', '🎟'),
    'contests': ('🏆', '🎯'),
}

_HELP = (
    '🧩 <b>Премиум-эмодзи</b>\n\n'
    '<code>/emoji https://t.me/addemoji/имя</code>: весь набор и подбор под иконки бота\n'
    '<code>/emoji 5258204546391351475</code>: набор, из которого этот эмодзи\n'
    '<code>/emoji</code> и эмодзи в том же сообщении или ответом на сообщение: их ID'
)


async def _send(message: types.Message, text: str) -> None:
    """A plain text message: ``Message.answer`` would put the logo over short ones (app/utils/message_patch.py)."""
    await message.bot.send_message(message.chat.id, text)


def _plain(emoji: str | None) -> str:
    """The emoji without variation selectors, so «ℹ️» and «ℹ» match."""
    return (emoji or '').replace('️', '')


def _show(emoji_id: str, emoji: str | None) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{html.escape(emoji or "⭐")}</tg-emoji>'


def _chunks(lines: list[str]) -> list[str]:
    """Lines grouped into messages that stay within Telegram's text and emoji limits."""
    messages: list[str] = []
    current: list[str] = []
    chars = emoji_count = 0
    for line in lines:
        line_emoji = line.count('<tg-emoji')
        if current and (chars + len(line) > _CHARS_PER_MESSAGE or emoji_count + line_emoji > _EMOJI_PER_MESSAGE):
            messages.append('\n'.join(current))
            current, chars, emoji_count = [], 0, 0
        current.append(line)
        chars += len(line) + 1
        emoji_count += line_emoji
    if current:
        messages.append('\n'.join(current))
    return messages


def _message_emoji(message: types.Message | None) -> dict[str, str]:
    """Premium emoji in a message: id → the plain emoji it is drawn over."""
    if message is None:
        return {}
    text = message.text or message.caption or ''
    found: dict[str, str] = {}
    for entity in message.entities or message.caption_entities or []:
        if entity.type == 'custom_emoji' and entity.custom_emoji_id:
            found.setdefault(entity.custom_emoji_id, entity.extract_from(text))
    return found


def _suggestion_lines(stickers: list[types.Sticker]) -> list[str]:
    """For every bot icon: its current look and up to four emoji from the pack that fit it."""
    lines = ['<b>Подбор под иконки бота</b> (сейчас → варианты из набора)']
    unmatched = []
    for key, icon in ICONS.items():
        own = _plain(icon.emoji)
        related = {_plain(emoji) for emoji in _RELATED.get(key, ())}
        exact = [sticker for sticker in stickers if _plain(sticker.emoji) == own]
        close = [sticker for sticker in stickers if _plain(sticker.emoji) in related]
        candidates = [*exact, *close][:_SUGGESTIONS_PER_ICON]
        if not candidates:
            unmatched.append(key)
            continue
        lines.append('')
        lines.append(f'{tg_emoji(key)} <b>{key}</b>')
        lines.extend(
            f'   {_show(sticker.custom_emoji_id, sticker.emoji)} <code>{sticker.custom_emoji_id}</code>'
            for sticker in candidates
        )
    if unmatched:
        lines.append('')
        lines.append('Без совпадений: ' + ', '.join(unmatched))
    return lines


async def _send_pack(message: types.Message, pack_name: str) -> None:
    try:
        sticker_set = await message.bot.get_sticker_set(name=pack_name)
    except TelegramBadRequest as error:
        logger.info('Набор эмодзи не найден', pack_name=pack_name, error=error)
        await message.reply(f'Набор <code>{html.escape(pack_name)}</code> не найден. Проверьте ссылку.')
        return

    stickers = [sticker for sticker in sticker_set.stickers if sticker.custom_emoji_id]
    if not stickers:
        await message.reply('Это набор стикеров, а не эмодзи: у его стикеров нет ID эмодзи.')
        return

    await message.reply(
        f'🧩 <b>{html.escape(sticker_set.title)}</b>: {len(stickers)} эмодзи\n'
        f'Ссылка: https://t.me/addemoji/{sticker_set.name}'
    )
    for text in _chunks(_suggestion_lines(stickers)):
        await _send(message, text)

    full_list = ['<b>Весь набор</b>']
    full_list.extend(
        f'{_show(sticker.custom_emoji_id, sticker.emoji)} <code>{sticker.custom_emoji_id}</code> '
        f'{html.escape(sticker.emoji or "")}'
        for sticker in stickers
    )
    for text in _chunks(full_list):
        await _send(message, text)


@admin_required
@error_handler
async def emoji_command(message: types.Message, db_user: User, db: AsyncSession):
    found = _message_emoji(message) or _message_emoji(message.reply_to_message)
    if found:
        lines = [f'<b>ID эмодзи</b>: {len(found)}']
        for emoji_id, emoji in found.items():
            lines.append(f'{_show(emoji_id, emoji)} <code>{emoji_id}</code> {html.escape(emoji)}')
        for text in _chunks(lines):
            await message.reply(text)
        return

    parts = (message.text or '').split(maxsplit=1)
    argument = parts[1].strip() if len(parts) > 1 else ''

    if _EMOJI_ID_RE.match(argument):
        stickers = await message.bot.get_custom_emoji_stickers(custom_emoji_ids=[argument])
        pack_name = stickers[0].set_name if stickers else None
        if not pack_name:
            await message.reply(f'Не удалось найти набор для эмодзи <code>{argument}</code>.')
            return
        await _send_pack(message, pack_name)
        return

    link = _PACK_LINK_RE.search(argument)
    if link:
        await _send_pack(message, link.group(1))
        return
    if _PACK_NAME_RE.match(argument):
        await _send_pack(message, argument)
        return

    await message.reply(_HELP)


def register_handlers(dp: Dispatcher):
    dp.message.register(emoji_command, Command('emoji'))
