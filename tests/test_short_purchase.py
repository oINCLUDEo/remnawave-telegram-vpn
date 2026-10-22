"""The purchase takes fewer taps: no list of one tariff, pay from the shortfall screen, connect after paying."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import settings
from app.handlers.subscription import tariff_purchase
from app.handlers.subscription.tariff_purchase import (
    get_purchase_success_keyboard,
    get_shortfall_keyboard,
)
from app.localization.texts import get_texts


def _targets(markup):
    return [
        [button.callback_data or button.url or getattr(button.web_app, 'url', None) for button in row]
        for row in markup.inline_keyboard
    ]


@pytest.fixture(autouse=True)
def _payment_settings(monkeypatch):
    monkeypatch.setattr(type(settings), 'is_multi_tariff_enabled', lambda self: False)
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'miniapp_subscription')


def test_shortfall_screen_lists_payment_methods_with_the_amount(monkeypatch):
    monkeypatch.setattr(settings, 'TELEGRAM_STARS_ENABLED', True)
    user = SimpleNamespace(language='ru', restriction_topup=False)

    rows = _targets(get_shortfall_keyboard(user, 15000, 'tariff_select:3'))

    assert ['topup_amount|stars|15000'] in rows
    assert rows[-1] == ['tariff_select:3']
    assert ['menu_balance'] not in rows  # the methods' own "Назад" is replaced


def test_restricted_top_up_keeps_the_explaining_screen():
    user = SimpleNamespace(language='ru', restriction_topup=True)

    rows = _targets(get_shortfall_keyboard(user, 15000, 'tariff_select:3'))

    assert rows == [['balance_topup'], ['tariff_select:3']]


def test_success_screen_offers_connect_first():
    subscription = SimpleNamespace(id=5, subscription_url='https://sub.example.com/x', subscription_crypto_link=None)

    rows = _targets(get_purchase_success_keyboard(get_texts('ru'), subscription))

    assert rows == [['https://sub.example.com/x'], ['menu_subscription', 'back_to_menu']]


def _callback(data):
    callback = MagicMock()
    callback.data = data
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    return callback


@pytest.fixture
def one_tariff(monkeypatch):
    tariff = SimpleNamespace(id=11, name='Base', is_active=True)
    monkeypatch.setattr(tariff_purchase, 'get_tariffs_for_user', AsyncMock(return_value=[tariff]))
    opened = AsyncMock()
    monkeypatch.setattr(tariff_purchase, 'open_tariff', opened)
    return opened


async def test_a_single_tariff_opens_directly(one_tariff):
    user = SimpleNamespace(language='ru', promo_group_id=None)
    state = AsyncMock()
    callback = _callback('menu_buy')

    await tariff_purchase.show_tariffs_list(callback, user, AsyncMock(), state)

    one_tariff.assert_awaited_once()
    assert one_tariff.await_args.args[-1] == 11
    callback.message.edit_text.assert_not_awaited()


async def test_back_from_the_single_tariff_leaves_the_purchase(one_tariff, monkeypatch):
    back_to_menu = AsyncMock()
    monkeypatch.setattr('app.handlers.menu.handle_back_to_menu', back_to_menu)
    user = SimpleNamespace(language='ru', promo_group_id=None)

    await tariff_purchase.show_tariffs_list(_callback('tariff_list'), user, AsyncMock(), AsyncMock())

    back_to_menu.assert_awaited_once()
    one_tariff.assert_not_awaited()
