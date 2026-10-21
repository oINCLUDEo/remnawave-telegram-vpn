"""The main menu is fixed in the bot and changes only with the user's state."""

from types import SimpleNamespace

import pytest

from app.config import settings
from app.keyboards.main_menu import MenuState, build_main_menu_keyboard, resolve_menu_state


def _sub(actual_status='active', *, is_trial=False, days_left=30, is_active=True, daily=False):
    return SimpleNamespace(
        actual_status=actual_status,
        is_trial=is_trial,
        days_left=days_left,
        is_active=is_active,
        tariff=SimpleNamespace(is_daily=daily),
        subscription_url='https://sub.example.com/abc',
        subscription_crypto_link=None,
    )


def _rows(markup):
    return [
        [button.callback_data or button.url or button.web_app.url for button in row] for row in markup.inline_keyboard
    ]


@pytest.fixture(autouse=True)
def _menu_settings(monkeypatch):
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'miniapp_subscription')
    monkeypatch.setattr(settings, 'CABINET_URL', 'https://cabinet.example.com')
    monkeypatch.setattr(settings, 'TRIAL_DISABLED_FOR', 'none')
    monkeypatch.setattr(type(settings), 'is_referral_program_enabled', lambda self: True)
    monkeypatch.setattr('app.keyboards.main_menu._is_support_enabled', lambda: True)
    # The cabinet's stored layout must not matter any more.
    monkeypatch.setattr(settings, 'MAIN_MENU_MODE', 'cabinet')


@pytest.mark.parametrize(
    ('subscription', 'expected'),
    [
        (None, MenuState.NEW),
        (_sub('pending', is_trial=True), MenuState.NEW),
        (_sub('active', is_trial=True, days_left=2), MenuState.TRIAL),
        (_sub('active', days_left=30), MenuState.ACTIVE),
        (_sub('active', days_left=3), MenuState.RENEW),
        (_sub('active', days_left=0, daily=True), MenuState.ACTIVE),
        (_sub('expired', days_left=0, is_active=False), MenuState.RENEW),
        (_sub('limited', is_active=False), MenuState.RENEW),
    ],
)
def test_resolve_menu_state(subscription, expected):
    assert resolve_menu_state(subscription) == expected


def test_new_user_sees_trial_first():
    rows = _rows(build_main_menu_keyboard('ru', subscription=None))

    assert rows == [
        ['menu_trial'],
        ['menu_buy', 'menu_balance'],
        ['menu_referrals', 'menu_support', 'menu_info'],
    ]


def test_buy_is_first_when_trial_already_used():
    rows = _rows(build_main_menu_keyboard('ru', subscription=None, has_had_paid_subscription=True))

    assert rows[0] == ['menu_buy']
    assert rows[1] == ['menu_balance']


def test_active_user_sees_connect_first():
    rows = _rows(build_main_menu_keyboard('ru', subscription=_sub()))

    assert rows == [
        ['https://sub.example.com/abc'],
        ['menu_subscription', 'menu_balance'],
        ['menu_referrals', 'menu_support', 'menu_info'],
    ]


def test_trial_user_is_offered_to_buy():
    rows = _rows(build_main_menu_keyboard('ru', subscription=_sub(is_trial=True, days_left=2)))

    assert rows[0] == ['https://sub.example.com/abc']
    assert rows[1] == ['menu_buy', 'menu_balance']


def test_expiring_user_sees_renew_first_and_can_still_connect():
    rows = _rows(build_main_menu_keyboard('ru', subscription=_sub(days_left=2)))

    assert rows[0] == ['subscription_extend', 'https://sub.example.com/abc']
    assert rows[1] == ['menu_subscription', 'menu_balance']


def test_expired_user_has_no_connect_button():
    rows = _rows(build_main_menu_keyboard('ru', subscription=_sub('expired', days_left=0, is_active=False)))

    assert rows[0] == ['subscription_extend']
    assert rows[1] == ['menu_subscription', 'menu_balance']


def test_secondary_items_are_not_on_the_main_menu():
    callbacks = {cb for row in _rows(build_main_menu_keyboard('ru', subscription=_sub())) for cb in row}

    assert not callbacks & {'menu_language', 'menu_promocode', 'contests_menu', 'buy_traffic'}


def test_disabled_sections_drop_out_without_breaking_rows(monkeypatch):
    monkeypatch.setattr(type(settings), 'is_referral_program_enabled', lambda self: False)

    rows = _rows(build_main_menu_keyboard('ru', subscription=_sub()))

    assert rows[2] == ['menu_support', 'menu_info']


def test_saved_cart_takes_the_place_of_buy():
    rows = _rows(build_main_menu_keyboard('ru', subscription=None, has_saved_cart=True))

    assert rows == [
        ['menu_trial'],
        ['return_to_saved_cart', 'menu_balance'],
        ['menu_referrals', 'menu_support', 'menu_info'],
    ]


@pytest.mark.parametrize(
    ('subscription', 'accent_callback', 'colour'),
    [
        (None, 'menu_trial', 'success'),
        (_sub(), None, 'primary'),  # Подключиться opens the subscription page
        (_sub(days_left=2), 'subscription_extend', 'success'),
    ],
)
def test_exactly_one_coloured_button(subscription, accent_callback, colour):
    markup = build_main_menu_keyboard('ru', subscription=subscription)
    coloured = [b for row in markup.inline_keyboard for b in row if b.style]

    assert len(coloured) == 1
    assert coloured[0].style == colour
    if accent_callback:
        assert coloured[0].callback_data == accent_callback


def test_renew_is_never_red():
    for subscription in (_sub(days_left=1), _sub('expired', days_left=0, is_active=False)):
        markup = build_main_menu_keyboard('ru', subscription=subscription)
        assert all(b.style != 'danger' for row in markup.inline_keyboard for b in row)


def test_admin_row_is_last():
    rows = _rows(build_main_menu_keyboard('ru', subscription=_sub(), is_admin=True))

    assert rows[-1] == ['admin_panel']


def test_buttons_carry_one_icon_each():
    markup = build_main_menu_keyboard('ru', subscription=None)
    trial = markup.inline_keyboard[0][0]
    buy, balance = markup.inline_keyboard[1]

    # Custom emoji icon: the label itself has no emoji.
    assert trial.icon_custom_emoji_id
    assert trial.text == 'Попробовать бесплатно'
    assert buy.icon_custom_emoji_id == '5427168083074628963'
    assert buy.text == 'Купить подписку'
    assert balance.icon_custom_emoji_id == '5258204546391351475'
    assert balance.text.startswith('Баланс: ')


def test_icon_without_custom_emoji_prefixes_unicode():
    from app.keyboards.icons import icon_button

    button = icon_button('promocode', 'Промокод', callback_data='menu_promocode')

    assert button.icon_custom_emoji_id is None
    assert button.text == '🎫 Промокод'


def test_consent_line_replaces_the_accept_screens(monkeypatch):
    from app.handlers.start import _with_consent_line

    monkeypatch.setattr(settings, 'SKIP_RULES_ACCEPT', False)
    assert _with_consent_line('Привет', 'ru') == 'Привет'

    monkeypatch.setattr(settings, 'SKIP_RULES_ACCEPT', True)
    text = _with_consent_line('Привет', 'ru')
    assert text.startswith('Привет\n\n')
    assert 'правила' in text
    assert '<' not in text  # sent without parse mode on HTML errors
