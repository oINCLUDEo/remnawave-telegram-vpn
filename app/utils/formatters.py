from datetime import UTC, datetime


def format_datetime(dt: datetime | str, format_str: str = '%d.%m.%Y %H:%M') -> str:
    if isinstance(dt, str):
        if dt == 'now' or dt == '':
            dt = datetime.now(UTC)
        else:
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                dt = datetime.now(UTC)

    return dt.strftime(format_str)


def format_date(dt: datetime | str, format_str: str = '%d.%m.%Y') -> str:
    if isinstance(dt, str):
        if dt == 'now' or dt == '':
            dt = datetime.now(UTC)
        else:
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                dt = datetime.now(UTC)

    return dt.strftime(format_str)


def format_time_ago(dt: datetime | str, language: str = 'ru') -> str:
    if isinstance(dt, str):
        if dt == 'now' or dt == '':
            dt = datetime.now(UTC)
        else:
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                dt = datetime.now(UTC)

    now = datetime.now(UTC)
    diff = now - dt

    language_code = (language or 'ru').split('-')[0].lower()

    if diff.days > 0:
        if diff.days == 1:
            return 'yesterday' if language_code == 'en' else 'вчера'
        if diff.days < 7:
            value = diff.days
            if language_code == 'en':
                suffix = 'day' if value == 1 else 'days'
                return f'{value} {suffix} ago'
            return f'{value} дн. назад'
        if diff.days < 30:
            value = diff.days // 7
            if language_code == 'en':
                suffix = 'week' if value == 1 else 'weeks'
                return f'{value} {suffix} ago'
            return f'{value} нед. назад'
        if diff.days < 365:
            value = diff.days // 30
            if language_code == 'en':
                suffix = 'month' if value == 1 else 'months'
                return f'{value} {suffix} ago'
            return f'{value} мес. назад'
        value = diff.days // 365
        if language_code == 'en':
            suffix = 'year' if value == 1 else 'years'
            return f'{value} {suffix} ago'
        return f'{value} г. назад'

    if diff.seconds > 3600:
        value = diff.seconds // 3600
        if language_code == 'en':
            suffix = 'hour' if value == 1 else 'hours'
            return f'{value} {suffix} ago'
        return f'{value} ч. назад'

    if diff.seconds > 60:
        value = diff.seconds // 60
        if language_code == 'en':
            suffix = 'minute' if value == 1 else 'minutes'
            return f'{value} {suffix} ago'
        return f'{value} мин. назад'

    return 'just now' if language_code == 'en' else 'только что'


_MONTHS_GENITIVE = {
    'ru': (
        'января',
        'февраля',
        'марта',
        'апреля',
        'мая',
        'июня',
        'июля',
        'августа',
        'сентября',
        'октября',
        'ноября',
        'декабря',
    ),
    'ua': (
        'січня',
        'лютого',
        'березня',
        'квітня',
        'травня',
        'червня',
        'липня',
        'серпня',
        'вересня',
        'жовтня',
        'листопада',
        'грудня',
    ),
    'fa': ('ژانویه', 'فوریه', 'مارس', 'آوریل', 'مه', 'ژوئن', 'ژوئیه', 'اوت', 'سپتامبر', 'اکتبر', 'نوامبر', 'دسامبر'),
}
_MONTHS_EN = (
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
)


def format_human_date(dt: datetime | None, language: str = 'ru') -> str:
    """A date as people say it, in the bot's timezone: «20 ноября», "November 20".

    The year is added only when it is not the current one. Payment and
    subscription messages use this instead of «20.11.2026 18:00».
    """
    from app.utils.timezone import to_local_datetime

    local = to_local_datetime(dt)
    if local is None:
        return ''
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code == 'uk':
        language_code = 'ua'
    show_year = local.year != to_local_datetime(datetime.now(UTC)).year

    if language_code == 'zh':
        text = f'{local.month}月{local.day}日'
        return f'{local.year}年{text}' if show_year else text
    if language_code == 'en':
        text = f'{_MONTHS_EN[local.month - 1]} {local.day}'
        return f'{text}, {local.year}' if show_year else text

    months = _MONTHS_GENITIVE.get(language_code, _MONTHS_GENITIVE['ru'])
    text = f'{local.day} {months[local.month - 1]}'
    return f'{text} {local.year}' if show_year else text


def _hours_phrase(hours: int, language: str, *, valid: bool) -> str:
    """«через 5 часов» / «ещё 5 часов» in the person's language; *hours* < 1 means «less than an hour»."""
    if language in {'ua', 'uk'}:
        if hours < 1:
            return 'ще менше години' if valid else 'менш ніж за годину'
        if hours == 1:
            return 'ще годину' if valid else 'через годину'
        word = _slavic_plural(hours, 'годину', 'години', 'годин')
        return f'ще {hours} {word}' if valid else f'через {hours} {word}'
    if language == 'zh':
        if hours < 1:
            return '还剩不到 1 小时' if valid else '不到 1 小时后'
        return f'还剩 {hours} 小时' if valid else f'{hours} 小时后'
    if language == 'fa':
        if hours < 1:
            return 'تا کمتر از یک ساعت دیگر' if valid else 'کمتر از یک ساعت دیگر'
        return f'تا {hours} ساعت دیگر' if valid else f'{hours} ساعت دیگر'
    if language == 'en':
        if hours < 1:
            return 'for less than an hour' if valid else 'in less than an hour'
        unit = 'hour' if hours == 1 else 'hours'
        return f'for {hours} more {unit}' if valid else f'in {hours} {unit}'
    if hours < 1:
        return 'ещё меньше часа' if valid else 'меньше чем через час'
    if hours == 1:
        return 'ещё час' if valid else 'через час'
    word = _slavic_plural(hours, 'час', 'часа', 'часов')
    return f'ещё {hours} {word}' if valid else f'через {hours} {word}'


def _days_phrase(days: int, language: str, *, valid: bool) -> str:
    """«через 3 дня» / «ещё 3 дня»."""
    count = format_days_declension(days, language)
    if language in {'ua', 'uk'}:
        return f'ще {count}' if valid else f'через {count}'
    if language == 'zh':
        return f'还剩 {count}' if valid else f'{count}后'
    if language == 'fa':
        return f'تا {count} دیگر' if valid else f'{count} دیگر'
    if language == 'en':
        return f'for {days} more day{"s" if days != 1 else ""}' if valid else f'in {count}'
    return f'ещё {count}' if valid else f'через {count}'


def _relative_deadline(dt: datetime | None, language: str, *, valid: bool) -> str:
    if dt is None:
        return ''
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code == 'uk':
        language_code = 'ua'
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    seconds = (dt - datetime.now(UTC)).total_seconds()
    hours = int(round(seconds / 3600))
    if hours < 48:
        return _hours_phrase(max(hours, 0), language_code, valid=valid)
    days = int(round(seconds / 86400))
    if days < 7:
        return _days_phrase(days, language_code, valid=valid)
    date = format_human_date(dt, language_code)
    if not valid:
        return {'en': f'on {date}'}.get(language_code, date)
    return {
        'en': f'until {date}',
        'zh': f'至{date}',
        'fa': f'تا {date}',
    }.get(language_code, f'до {date}')


def format_time_left(dt: datetime | None, language: str = 'ru') -> str:
    """When something ends, without clock time: «через 5 часов», «через 3 дня», «20 ноября».

    The bot does not know the person's time zone, so «завтра в 18:00» can be
    wrong by hours, while a count of hours is right everywhere. Fits
    «закончится {…}».
    """
    return _relative_deadline(dt, language, valid=False)


def format_valid_for(dt: datetime | None, language: str = 'ru') -> str:
    """How long something lasts, without clock time: «ещё 5 часов», «ещё 3 дня», «до 20 ноября».

    Fits «скидка действует {…}».
    """
    return _relative_deadline(dt, language, valid=True)


def format_remaining(dt: datetime | None, language: str = 'ru') -> str:
    """What is left until *dt*, without a date: «осталось 29 дней», «остался 1 час», «осталось меньше часа».

    Fits after a date that is already on screen: «Активна до 1 декабря, осталось 29 дней».
    Days are whole days left, so the count never promises more than there is.
    """
    if dt is None:
        return ''
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code == 'uk':
        language_code = 'ua'
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    seconds = max((dt - datetime.now(UTC)).total_seconds(), 0)
    hours = int(seconds // 3600)
    in_days = hours >= 48
    count = int(seconds // 86400) if in_days else hours

    if language_code == 'ua':
        if count < 1:
            return 'залишилося менше години'
        word = (
            _slavic_plural(count, 'день', 'дні', 'днів')
            if in_days
            else _slavic_plural(count, 'година', 'години', 'годин')
        )
        return f'ще {count} {word}'
    if language_code == 'zh':
        if count < 1:
            return '还剩不到 1 小时'
        return f'还剩 {count} 天' if in_days else f'还剩 {count} 小时'
    if language_code == 'fa':
        if count < 1:
            return 'کمتر از یک ساعت مانده'
        return f'{count} روز مانده' if in_days else f'{count} ساعت مانده'
    if language_code != 'ru':
        if count < 1:
            return 'less than an hour left'
        unit = 'day' if in_days else 'hour'
        return f'{count} {unit}{"s" if count != 1 else ""} left'

    if count < 1:
        return 'осталось меньше часа'
    word = (
        _slavic_plural(count, 'день', 'дня', 'дней') if in_days else _slavic_plural(count, 'час', 'часа', 'часов')
    )
    verb = 'остался' if count % 10 == 1 and count % 100 != 11 else 'осталось'
    return f'{verb} {count} {word}'


def format_gb(value: float | int | None, language: str = 'ru') -> str:
    """Gigabytes as a number people read: «12,4», «8», "12.4". The unit is up to the sentence."""
    text = f'{float(value or 0):.1f}'
    if text.endswith('.0'):
        text = text[:-2]
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code in {'ru', 'ua', 'uk'}:
        text = text.replace('.', ',')
    return text


def format_days_declension(days: int, language: str = 'ru') -> str:
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code in {'ua', 'uk'}:
        if days % 10 == 1 and days % 100 != 11:
            return f'{days} день'
        if days % 10 in [2, 3, 4] and days % 100 not in [12, 13, 14]:
            return f'{days} дні'
        return f'{days} днів'
    if language_code == 'zh':
        return f'{days} 天'
    if language_code == 'fa':
        return f'{days} روز'
    if language_code != 'ru':
        return f'{days} day{"s" if days != 1 else ""}'

    if days % 10 == 1 and days % 100 != 11:
        return f'{days} день'
    if days % 10 in [2, 3, 4] and days % 100 not in [12, 13, 14]:
        return f'{days} дня'
    return f'{days} дней'


def _slavic_plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


def format_devices_count(count: int, language: str = 'ru') -> str:
    """«1 устройство», «3 устройства», "2 devices"."""
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code in {'ua', 'uk'}:
        return f'{count} {_slavic_plural(count, "пристрій", "пристрої", "пристроїв")}'
    if language_code == 'zh':
        return f'{count} 台设备'
    if language_code == 'fa':
        return f'{count} دستگاه'
    if language_code != 'ru':
        return f'{count} device{"s" if count != 1 else ""}'
    return f'{count} {_slavic_plural(count, "устройство", "устройства", "устройств")}'


def format_friends_count(count: int, language: str = 'ru') -> str:
    """Friends as the object of «привели»: «1 друга», «3 друга», «5 друзей»; "2 friends"."""
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code in {'ua', 'uk'}:
        return f'{count} {_slavic_plural(count, "друга", "друзів", "друзів")}'
    if language_code == 'zh':
        return f'{count} 位朋友'
    if language_code == 'fa':
        return f'{count} دوست'
    if language_code != 'ru':
        return f'{count} friend{"s" if count != 1 else ""}'
    return f'{count} {_slavic_plural(count, "друга", "друга", "друзей")}'


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f'{seconds} сек.'

    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes} мин.'

    hours = minutes // 60
    if hours < 24:
        return f'{hours} ч.'

    days = hours // 24
    return f'{days} дн.'


def format_bytes(bytes_value: int) -> str:
    if bytes_value == 0:
        return '0 B'

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(bytes_value)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if size == int(size):
        return f'{int(size)} {units[unit_index]}'
    return f'{size:.1f} {units[unit_index]}'


def format_percentage(value: float, decimals: int = 1) -> str:
    return f'{value:.{decimals}f}%'


def format_number(number: float, separator: str = ' ') -> str:
    if isinstance(number, float):
        integer_part = int(number)
        decimal_part = number - integer_part

        formatted_integer = f'{integer_part:,}'.replace(',', separator)

        if decimal_part > 0:
            return f'{formatted_integer}.{decimal_part:.2f}'.split('.')[0] + f'.{str(decimal_part).split(".")[1][:2]}'
        return formatted_integer
    return f'{number:,}'.replace(',', separator)


def format_price_range(min_price: int, max_price: int) -> str:
    from app.config import settings

    min_formatted = settings.format_price(min_price)
    max_formatted = settings.format_price(max_price)

    if min_price == max_price:
        return min_formatted
    return f'{min_formatted} - {max_formatted}'


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_username(username: str | None, user_id: int, full_name: str | None = None) -> str:
    if full_name:
        return full_name
    if username:
        return f'@{username}'
    return f'ID{user_id}'


def format_subscription_status(is_active: bool, is_trial: bool, end_date: datetime | str, language: str = 'ru') -> str:
    if isinstance(end_date, str):
        try:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            end_date = datetime.now(UTC)

    language_code = (language or 'ru').split('-')[0].lower()
    use_russian_fallback = language_code in {'ru', 'fa'}

    if not is_active:
        return '❌ Неактивна' if use_russian_fallback else '❌ Inactive'

    if is_trial:
        status = '🎁 Тестовая' if use_russian_fallback else '🎁 Trial'
    else:
        status = '✅ Активна' if use_russian_fallback else '✅ Active'

    now = datetime.now(UTC)
    if end_date > now:
        days_left = (end_date - now).days
        if days_left > 0:
            status += f' ({days_left} дн.)' if use_russian_fallback else f' ({days_left} days)'
        else:
            hours_left = (end_date - now).seconds // 3600
            status += f' ({hours_left} ч.)' if use_russian_fallback else f' ({hours_left} hrs)'
    else:
        status = '⏰ Истекла' if use_russian_fallback else '⏰ Expired'

    return status


def format_traffic_usage(used_gb: float, limit_gb: int, language: str = 'ru') -> str:
    language_code = (language or 'ru').split('-')[0].lower()
    use_russian_fallback = language_code in {'ru', 'fa'}

    if limit_gb == 0:
        if use_russian_fallback:
            return f'{used_gb:.1f} ГБ / ∞'
        return f'{used_gb:.1f} GB / ∞'

    percentage = (used_gb / limit_gb) * 100 if limit_gb > 0 else 0

    if use_russian_fallback:
        return f'{used_gb:.1f} ГБ / {limit_gb} ГБ ({percentage:.1f}%)'
    return f'{used_gb:.1f} GB / {limit_gb} GB ({percentage:.1f}%)'


def format_boolean(value: bool, language: str = 'ru') -> str:
    language_code = (language or 'ru').split('-')[0].lower()
    if language_code in {'ru', 'fa'}:
        return '✅ Да' if value else '❌ Нет'
    return '✅ Yes' if value else '❌ No'
