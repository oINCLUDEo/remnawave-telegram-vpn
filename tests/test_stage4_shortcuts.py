"""Quick top-up amounts, one-tap referral sharing and a direct support chat."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

from app.config import settings
from app.handlers.balance import main as balance
from app.handlers.referral import build_referral_share_url
from app.keyboards.inline import get_referral_keyboard
from app.keyboards.main_menu import build_main_menu_keyboard
from app.localization.texts import get_texts


def _targets(markup):
    return [[button.callback_data or button.url for button in row] for row in markup.inline_keyboard]


def test_quick_amounts_are_the_owners_choice():
    rows = _targets(balance.get_quick_topup_amounts_keyboard('ru'))

    assert rows == [
        ['balance_topup_amount:100', 'balance_topup_amount:200', 'balance_topup_amount:300'],
        ['balance_topup_amount:500', 'balance_topup_amount:1000'],
        ['balance_topup_other'],
        ['menu_balance'],
    ]


def _callback(data):
    callback = MagicMock()
    callback.data = data
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    return callback


@pytest.fixture
def no_cart(monkeypatch):
    monkeypatch.setattr('app.services.user_cart_service.user_cart_service.get_user_cart', AsyncMock(return_value=None))
    monkeypatch.setattr(balance, '_has_automatic_payment_methods', lambda: True)
    monkeypatch.setattr(settings, 'TELEGRAM_STARS_ENABLED', True)


def _user():
    return SimpleNamespace(id=1, language='ru', restriction_topup=False)


async def test_top_up_asks_for_the_amount_first(no_cart):
    callback = _callback('balance_topup')

    await balance.show_payment_methods(callback, _user(), AsyncMock(), AsyncMock())

    markup = callback.message.edit_text.await_args.kwargs['reply_markup']
    assert _targets(markup)[0][0] == 'balance_topup_amount:100'


async def test_picked_amount_is_filled_into_every_method(no_cart):
    callback = _callback('balance_topup_amount:300')

    await balance.show_payment_methods(callback, _user(), AsyncMock(), AsyncMock())

    rows = _targets(callback.message.edit_text.await_args.kwargs['reply_markup'])
    assert ['topup_amount|stars|30000'] in rows
    assert rows[-1] == ['balance_topup']  # back to the amounts


async def test_other_amount_keeps_the_typed_flow(no_cart):
    callback = _callback('balance_topup_other')

    await balance.show_payment_methods(callback, _user(), AsyncMock(), AsyncMock())

    rows = _targets(callback.message.edit_text.await_args.kwargs['reply_markup'])
    assert ['topup_stars'] in rows


def test_share_link_opens_the_chat_picker_with_the_referral_link():
    url = build_referral_share_url(get_texts('ru'), 'https://t.me/ulya_bot?start=ref_ABC')

    parsed = urlparse(url)
    assert f'{parsed.netloc}{parsed.path}' == 't.me/share/url'
    assert parse_qs(parsed.query)['url'] == ['https://t.me/ulya_bot?start=ref_ABC']

    rows = _targets(get_referral_keyboard('ru', share_url=url))
    assert rows[0] == [url]
    assert rows[1] == ['referral_show_qr', 'referral_list', 'referral_analytics']


def test_without_a_link_the_invite_screen_is_offered():
    assert build_referral_share_url(get_texts('ru'), None) is None
    assert _targets(get_referral_keyboard('ru'))[0] == ['referral_create_invite']


@pytest.mark.parametrize(
    ('tickets', 'contact', 'expected'),
    [(False, True, 'https://t.me/ulya_support'), (True, True, 'menu_support'), (False, False, 'menu_support')],
)
def test_support_opens_the_chat_when_it_is_the_only_channel(monkeypatch, tickets, contact, expected):
    from app.services.support_settings_service import SupportSettingsService

    monkeypatch.setattr(SupportSettingsService, 'is_tickets_enabled', classmethod(lambda cls: tickets))
    monkeypatch.setattr(SupportSettingsService, 'is_contact_enabled', classmethod(lambda cls: contact))
    monkeypatch.setattr('app.keyboards.main_menu._is_support_enabled', lambda: True)
    monkeypatch.setattr(type(settings), 'get_support_contact_url', lambda self: 'https://t.me/ulya_support')
    monkeypatch.setattr(type(settings), 'is_referral_program_enabled', lambda self: True)
    monkeypatch.setattr(settings, 'TRIAL_DISABLED_FOR', 'none')

    rows = _targets(build_main_menu_keyboard('ru', subscription=None))

    assert rows[2][1] == expected
