"""The "Моя подписка" screen: four rows at most, one accent, no dead end."""

from types import SimpleNamespace

import pytest

from app.config import settings
from app.keyboards.inline import (
    get_no_subscription_keyboard,
    get_subscription_keyboard,
    get_updated_subscription_settings_keyboard,
)
from app.localization.texts import get_texts


def _sub(*, is_trial=False, days_left=30, actual_status='active', daily=False, paused=False, traffic_limit_gb=0):
    tariff = SimpleNamespace(is_daily=daily, can_topup_traffic=lambda: True) if daily is not None else None
    return SimpleNamespace(
        id=7,
        actual_status=actual_status,
        status=actual_status,
        is_trial=is_trial,
        days_left=days_left,
        is_active=actual_status == 'active',
        is_daily_paused=paused,
        tariff=tariff,
        traffic_limit_gb=traffic_limit_gb,
        subscription_url='https://sub.example.com/abc',
        subscription_crypto_link=None,
    )


def _targets(markup):
    return [
        [button.callback_data or button.url or button.web_app.url for button in row] for row in markup.inline_keyboard
    ]


@pytest.fixture(autouse=True)
def _screen_settings(monkeypatch):
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'miniapp_subscription')
    monkeypatch.setattr(settings, 'MULTI_TARIFF_ENABLED', False, raising=False)
    monkeypatch.setattr(type(settings), 'is_multi_tariff_enabled', lambda self: False)
    monkeypatch.setattr(type(settings), 'is_tariffs_mode', lambda self: True)
    monkeypatch.setattr(type(settings), 'is_happ_download_button_enabled', lambda self: False)


def test_paid_subscription_has_four_rows():
    rows = _targets(get_subscription_keyboard('ru', has_subscription=True, subscription=_sub()))

    assert rows == [
        ['https://sub.example.com/abc'],
        ['subscription_extend', 'instant_switch'],
        ['subscription_manage_devices', 'subscription_settings'],
        ['back_to_menu'],
    ]


def test_trial_is_offered_to_buy():
    rows = _targets(
        get_subscription_keyboard('ru', has_subscription=True, is_trial=True, subscription=_sub(is_trial=True))
    )

    assert rows == [['https://sub.example.com/abc'], ['subscription_upgrade'], ['back_to_menu']]


def test_daily_tariff_pauses_instead_of_renewing():
    rows = _targets(get_subscription_keyboard('ru', has_subscription=True, subscription=_sub(daily=True)))

    assert rows[1] == ['toggle_daily_subscription_pause', 'tariff_switch']


def test_connect_is_the_accent_while_access_is_fine():
    markup = get_subscription_keyboard('ru', has_subscription=True, subscription=_sub())
    coloured = [b for row in markup.inline_keyboard for b in row if b.style]

    assert [b.style for b in coloured] == ['primary']


def test_renew_takes_the_accent_when_ending_soon():
    markup = get_subscription_keyboard('ru', has_subscription=True, subscription=_sub(days_left=2))
    coloured = [b for row in markup.inline_keyboard for b in row if b.style]

    assert len(coloured) == 1
    assert coloured[0].callback_data == 'subscription_extend'
    assert coloured[0].style == 'success'


@pytest.mark.parametrize(('trial_available', 'expected'), [(True, ['menu_trial', 'menu_buy']), (False, ['menu_buy'])])
def test_no_subscription_is_not_a_dead_end(trial_available, expected):
    rows = _targets(get_no_subscription_keyboard('ru', trial_available=trial_available))

    assert [row[0] for row in rows[:-1]] == expected
    assert rows[-1] == ['back_to_menu']


def test_settings_carry_autopay_and_traffic():
    tariff = SimpleNamespace(is_daily=False, can_topup_traffic=lambda: True, device_price_kopeks=0)
    rows = _targets(
        get_updated_subscription_settings_keyboard(
            'ru', show_countries_management=False, tariff=tariff, subscription=_sub(traffic_limit_gb=100)
        )
    )

    assert ['subscription_autopay'] in rows
    assert ['buy_traffic'] in rows
    assert ['subscription_manage_devices'] not in rows  # it is on the subscription screen now
    assert rows[-1] == ['menu_subscription']


@pytest.mark.parametrize('language', ['ru', 'en', 'ua', 'zh', 'fa'])
@pytest.mark.parametrize('key', ['SUBSCRIPTION_OVERVIEW_TEMPLATE', 'SUBSCRIPTION_DAILY_OVERVIEW_TEMPLATE'])
def test_overview_templates_format_in_every_language(language, key):
    template = get_texts(language).t(key, '')
    text = template.format(
        title='T',
        date_icon='D',
        devices_line='',
        full_name='',
        balance='',
        status_emoji='S',
        status_display='Active',
        warning='',
        tariff_info_block='',
        subscription_type='',
        end_date='01.01.2027',
        time_left='3',
        traffic='1 / 2',
        servers='NL',
        devices_used='1',
        device_limit='3',
    )

    assert text.startswith('T\n\nS <b>Active</b>')
    assert text.count('<blockquote>') == text.count('</blockquote>') == 1
