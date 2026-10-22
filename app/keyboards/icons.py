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


# Custom emoji ids were checked by the owner. Most come from one colour animated
# pack, the one 💎 5427168083074628963 belongs to (admin ``/emoji
# 5427168083074628963`` lists it), so the icons share one style; keep to that
# pack when adding icons. Where it has nothing that fits, the icon comes from
# the pack 💳 belongs to or from «TG iOS & macOS Icons»
# (https://t.me/addemoji/tgmacicons). The Unicode emoji is the nearest plain
# emoji, used where Telegram cannot draw the custom one.
ICONS: dict[str, Icon] = {
    'connect': Icon('🌐', '5447410659077661506'),
    'subscription': Icon('💎', '5427168083074628963'),
    'buy': Icon('💎', '5427168083074628963'),
    'trial': Icon('🎁', '5203996991054432397'),
    'renew': Icon('🔄', '5386367538735104399'),
    'checkout': Icon('🛍', '5406683434124859552'),
    'balance': Icon('💰', '5231449120635370684'),
    'payment': Icon('💳', '5220048868682532055'),
    'referral': Icon('✉️', '5253742260054409879'),
    'support': Icon('💬', '5443038326535759644'),
    'cabinet': Icon('🏠', '5416041192905265756'),
    'info': Icon('ℹ️', '5334544901428229844'),
    'tariff': Icon('📦', '5854908544712707500'),
    'devices': Icon('📱', '5258423306255604960'),
    'settings': Icon('⚙️', '5341715473882955310'),
    # Autopay renews the subscription, so it wears the renewal icon, not the payment card.
    'autopay': Icon('🔄', '5386367538735104399'),
    'traffic': Icon('📈', '5244837092042750681'),
    'pause': Icon('⏸️', '5359543311897998264'),
    'resume': Icon('▶️', '5348125953090403204'),
    # Statuses and values in message text. The first line of a message carries
    # one of them: the object's icon when all is well, ⚠️ when the user needs to
    # act, 🚫 when access has ended, ❌ only when something broke on our side.
    'warning': Icon('⚠️', '5447644880824181073'),
    'expired': Icon('🚫', '5240241223632954241'),
    'date': Icon('📅', '5413879192267805083'),
    'language': Icon('🌍', '5260512129240276089'),
    'promocode': Icon('🎫', '5229064374403998351'),
    'contests': Icon('🥇', '5440539497383087970'),
    'admin': Icon('⚙️', '5341715473882955310'),
    'moderation': Icon('🛡', '5251203410396458957'),
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


def tg_emoji(icon_key: str) -> str:
    """The icon for message text (HTML): the custom emoji when there is one."""
    icon = ICONS[icon_key]
    if icon.custom_emoji_id:
        return f'<tg-emoji emoji-id="{icon.custom_emoji_id}">{icon.emoji}</tg-emoji>'
    return icon.emoji


def screen_title(icon_key: str, title: str) -> str:
    """The first line of a screen: the section's icon and its name in bold.

    A screen opened from a button starts with that button's icon, so the user
    sees where they landed.
    """
    return f'{tg_emoji(icon_key)} <b>{title}</b>'


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
