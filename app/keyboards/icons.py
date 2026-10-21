"""One icon per concept, used by every button that names that concept.

Before this module the same idea wore different emoji depending on the screen:
the subscription was 📱, 💎 or 🛡, money was 💰 or 💳, and the referral section
was called both "Партнерка" and "Реф. система". Buttons now take their icon from
here, so a change made once shows up everywhere.

Each icon has a Unicode emoji and, optionally, a Telegram custom emoji. When the
custom emoji is set, Telegram draws it as the button's own icon
(``icon_custom_emoji_id``, aiogram >= 3.25) and the label carries no emoji of
its own; otherwise the Unicode emoji is prefixed to the label. Custom emoji on
buttons need the bot owner to have Telegram Premium.
"""

from dataclasses import dataclass

from aiogram import types
from aiogram.types import InlineKeyboardButton


@dataclass(frozen=True)
class Icon:
    emoji: str
    custom_emoji_id: str | None = None


ICONS: dict[str, Icon] = {
    'connect': Icon('🚀'),
    'subscription': Icon('💎', '5427168083074628963'),
    'buy': Icon('💎', '5427168083074628963'),
    'trial': Icon('🎁', '5203996991054432397'),
    'renew': Icon('🔄', '5258419835922030550'),
    'checkout': Icon('🛒'),
    'balance': Icon('💰'),
    'payment': Icon('💳'),
    'referral': Icon('🤝'),
    'support': Icon('💬'),
    'cabinet': Icon('🌐'),
    'info': Icon('ℹ️'),
    'language': Icon('🌍'),
    'promocode': Icon('🎫'),
    'contests': Icon('🎲'),
    'admin': Icon('⚙️'),
    'moderation': Icon('🧑‍⚖️'),
}

# Button colours (Telegram Bot API 9.4 ``style``). Colour says what kind of
# action a button is, never which section it belongs to:
#
#   STYLE_PAY     зелёная  — получить или оплатить доступ: попробовать, купить,
#                            продлить, оплатить, продолжить оформление;
#   STYLE_USE     синяя    — пользоваться тем, что уже есть: подключиться,
#                            открыть инструкцию;
#   STYLE_DANGER  красная  — необратимое: удалить подписку, сбросить устройства,
#                            отвязать карту; только на кнопке подтверждения;
#   без цвета              — навигация и всё остальное, включая «Назад».
#
# At most one coloured button per screen, the one the user most likely needs
# next (``main_menu.keep_single_accent`` enforces it on the main menu). An
# expiring subscription is signalled in the text (⚠️), not with a red "renew":
# renewing is a purchase, so it is green like every other purchase.
STYLE_PAY = 'success'
STYLE_USE = 'primary'
STYLE_DANGER = 'danger'


def icon_label(icon_key: str, text: str) -> str:
    """Return *text* with the icon's Unicode emoji, for places that take plain text."""
    icon = ICONS[icon_key]
    return f'{icon.emoji} {text}'


def icon_button(
    icon_key: str,
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    web_app_url: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    """Build a button whose icon comes from :data:`ICONS`.

    *text* is the bare label without an emoji. Exactly one of *callback_data*,
    *url* or *web_app_url* must be given.
    """
    icon = ICONS[icon_key]
    label = text if icon.custom_emoji_id else f'{icon.emoji} {text}'

    kwargs: dict = {}
    if web_app_url:
        kwargs['web_app'] = types.WebAppInfo(url=web_app_url)
    elif url:
        kwargs['url'] = url
    else:
        kwargs['callback_data'] = callback_data

    return InlineKeyboardButton(
        text=label,
        style=style,
        icon_custom_emoji_id=icon.custom_emoji_id,
        **kwargs,
    )
