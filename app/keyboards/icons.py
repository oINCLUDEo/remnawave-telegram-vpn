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


# The bot's icon system (the catalogue with every id and pack is kept outside the
# repo, in the project files: emoji/catalog.md; admin /emoji icons shows it):
#
# - the base is monochrome, in the spirit of Apple: white line icons from one
#   static pack (/emoji 5776375003280838798), on every button, screen title and
#   icon in text. Buttons get no colour icons: their colour is their ``style``;
# - colour means a status, and a message carries one at most: ok, warning,
#   expired, error, celebrate, from the colour animated pack 💎 used to belong
#   to (/emoji 5427168083074628963). The plain status emoji ✅ ❌ ⚠️ 🚫 in a
#   text become that colour icon the first time and line icons after it
#   (app/keyboards/text_icons.py), so a list of ✅ stays calm;
# - locales and code write plain emoji. The bot's session turns those in
#   EMOJI_KEYS into these icons on the way out (button_icons.py, text_icons.py),
#   so a concept is restyled here, once, and never by hardcoding a
#   ``<tg-emoji>`` id in a text.
#
# The ids were read off screenshots; the bot checks them with Telegram at
# startup and switches off any it does not know (drop_unknown_icons). The
# Unicode emoji is what Telegram shows where it cannot draw the custom one.
ICONS: dict[str, Icon] = {
    'connect': Icon('🪐', '5879585266426973039'),
    'subscription': Icon('💎', '5807465992363710697'),
    'buy': Icon('💎', '5807465992363710697'),
    'trial': Icon('🎁', '5963213811597970978'),
    'renew': Icon('🕔', '6005843436479975944'),
    'checkout': Icon('🛒'),
    'balance': Icon('💰', '5769403330761593044'),
    'payment': Icon('💳', '5927169041595634481'),
    # A lightning bolt: СБП is the fast way to pay.
    'sbp': Icon('🏦', '5843553939672274145'),
    'star': Icon('⭐', '5874948844935974490'),
    'history': Icon('🕘', '5778202206922608769'),
    'referral': Icon('🤝', '5944970130554359187'),
    'support': Icon('🤙', '5884510167986343350'),
    'cabinet': Icon('👤', '5879770735999717115'),
    'info': Icon('ℹ️', '5879785854284599288'),
    'tariff': Icon('📦', '5924720918826848520'),
    'devices': Icon('📱', '5877318502947229960'),
    'android': Icon('🤖', '5819078828017849357'),
    'apple': Icon('🍎', '5818920837645867167'),
    'windows': Icon('💻', '5818956713507689486'),
    'settings': Icon('⚙️', '5877260593903177342'),
    # Autopay renews the subscription, so it wears the renewal icon, not the payment card.
    'autopay': Icon('🕔', '6005843436479975944'),
    'traffic': Icon('📈', '5874986954180791957'),
    'pause': Icon('⏸️'),
    'resume': Icon('▶️'),
    'date': Icon('🗓', '5967412305338568701'),
    'language': Icon('🌍', '5778184941154078090'),
    'globe': Icon('🌐', '5879585266426973039'),
    'promocode': Icon('🎫', '5854776233950188167'),
    'contests': Icon('🎲', '5960608239623082921'),
    'admin': Icon('⚙️', '5877260593903177342'),
    'moderation': Icon('🧑‍⚖️', '6028226658543082010'),
    'bell': Icon('🔔', '5909201569898827582'),
    'hint': Icon('💡', '5994473545650934240'),
    'tools': Icon('🔧', '5988023995125993550'),
    # Everyday actions. Most buttons get these from the emoji at the start of
    # their label (app/keyboards/button_icons.py), not by key.
    'back': Icon('⬅️', '5875082500023258804'),
    'home': Icon('🏠', '6008258140108231117'),
    'refresh': Icon('🔄', '5845943483382110702'),
    'stats': Icon('📊', '5931472654660800739'),
    'list': Icon('📋', '5875462364110787088'),
    'edit': Icon('✏️', '5879841310902324730'),
    'add': Icon('➕', '5775937998948404844'),
    'delete': Icon('🗑', '5879896690210639947'),
    'search': Icon('🔍', '5874960879434338403'),
    'view': Icon('👁', '5960714428394507968'),
    'link': Icon('🔗', '5877465816030515018'),
    'share': Icon('📤', '5877540355187937244'),
    'download': Icon('⬇️', '5879883461711367869'),
    'send': Icon('📨', '5875465628285931233'),
    'chat': Icon('💬', '5886666250158870040'),
    'announce': Icon('📢', '5771695636411847302'),
    'document': Icon('📄', '5956561916573782596'),
    'guide': Icon('❓', '5873121512445187130'),
    'lock': Icon('🔒', '5879895758202735862'),
    'calendar': Icon('📅', '5967412305338568701'),
    'time': Icon('⏳', '5776213190387961618'),
    'people': Icon('👥', '5942877472163892475'),
    'profile': Icon('👤', '5879770735999717115'),
    'coin': Icon('🪙', '5992430854909989581'),
    # Points down to the menu: the last line of the main menu text.
    'down': Icon('🔽', '5875008416132370818'),
    # Statuses in line form: a list item, or a status after the message's first one.
    'check': Icon('✅', '5776375003280838798'),
    'cross': Icon('❌', '5778527486270770928'),
    'attention': Icon('⚠️', '5881702736843511327'),
    'block': Icon('🚫', '5872829476143894491'),
    # Statuses in colour, one per message. The first line of a message says
    # how things are: ok when all is well, warning when the user needs to act,
    # expired when access has ended, error only when something broke on our side.
    'ok': Icon('✅', '5206607081334906820'),
    'warning': Icon('⚠️', '5447644880824181073'),
    'expired': Icon('🚫', '5240241223632954241'),
    'error': Icon('❌', '5210952531676504517'),
    'celebrate': Icon('🎉', '5461151367559141950'),
}

# The colour form of each line status: the first status in a message is drawn in colour.
STATUS_ACCENTS: dict[str, str] = {
    'check': 'ok',
    'attention': 'warning',
    'block': 'expired',
    'cross': 'error',
}
ACCENT_KEYS = frozenset({*STATUS_ACCENTS.values(), 'celebrate'})

# A plain emoji in a label or a text → the ICONS key drawn in its place. Written
# without the variation selector (U+FE0F); texts match with or without it.
# Left out on purpose: flags, the coloured circles of server status (🟢 🟡 🔴),
# digits, and emoji that have no icon of their own here.
EMOJI_KEYS: dict[str, str] = {
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
    '💡': 'hint',
    '🔒': 'lock',
    '🔐': 'lock',
    '🔑': 'lock',
    '🛡': 'lock',
    '📅': 'calendar',
    '📆': 'calendar',
    '🗓': 'date',
    '⏳': 'time',
    '⌛': 'time',
    '⏰': 'time',
    '⏱': 'time',
    '🕐': 'time',
    '🕒': 'time',
    '🕘': 'history',
    '🕔': 'renew',
    '👥': 'people',
    '🤝': 'referral',
    '👤': 'profile',
    '🆔': 'profile',
    '🪙': 'coin',
    '💸': 'coin',
    '💵': 'coin',
    '🔽': 'down',
    '⚙': 'settings',
    '🔧': 'tools',
    '🛠': 'tools',
    '📱': 'devices',
    '📺': 'devices',
    '🤖': 'android',
    '🍎': 'apple',
    '💻': 'windows',
    '📈': 'traffic',
    '💰': 'balance',
    '💳': 'payment',
    '🏦': 'sbp',
    '⚡': 'sbp',
    '⭐': 'star',
    'ℹ': 'info',
    '🤙': 'support',
    '🆘': 'support',
    '🛟': 'support',
    '🎫': 'promocode',
    '🎲': 'contests',
    '🏆': 'contests',
    '🔔': 'bell',
    '🌐': 'globe',
    '🌍': 'globe',
    # 🌐 and 🌍 mostly mean servers and countries; the language screen writes 🔤.
    '🔤': 'language',
    '🪐': 'connect',
    '🚀': 'connect',
    '💎': 'subscription',
    '📦': 'tariff',
    '🎁': 'trial',
    '✅': 'check',
    '✔': 'check',
    '❌': 'cross',
    '✖': 'cross',
    '⚠': 'attention',
    '❗': 'attention',
    '🚫': 'block',
    '⛔': 'block',
    '🎉': 'celebrate',
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


async def drop_unknown_icons(bot) -> tuple[list[str], list[str]]:
    """Ask Telegram about every icon; switch off the ones it does not know.

    The ids were copied from screenshots, and one wrong digit would make a
    button or a text fail. An unknown icon falls back to its Unicode emoji.
    Returns the unknown keys and the keys of the monochrome base that turned
    out animated (only reported: the base should be the static pack).
    """
    ids = sorted({icon.custom_emoji_id for icon in ICONS.values() if icon.custom_emoji_id})
    stickers = {}
    for start in range(0, len(ids), 200):  # the Bot API's limit per call
        for sticker in await bot.get_custom_emoji_stickers(custom_emoji_ids=ids[start : start + 200]):
            stickers[sticker.custom_emoji_id] = sticker

    unknown, animated = [], []
    for key, icon in ICONS.items():
        if not icon.custom_emoji_id:
            continue
        sticker = stickers.get(icon.custom_emoji_id)
        if sticker is None:
            unknown.append(key)
            ICONS[key] = Icon(icon.emoji)
        elif key not in ACCENT_KEYS and (sticker.is_animated or sticker.is_video):
            animated.append(key)
    return unknown, animated


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
