"""Each section shows its own banner once the file exists, the logo otherwise."""

import pytest

from app.utils import banners, message_patch
from app.utils.banners import banner_key_for_callback, banner_key_for_message, set_current_banner


@pytest.mark.parametrize(
    ('data', 'key'),
    [
        ('back_to_menu', 'main'),
        ('menu_subscription', 'subscription'),
        ('menu_buy', 'buy'),
        ('tariff_select:3', 'buy'),
        ('tariff_extend:3', 'renew'),
        ('subscription_extend', 'renew'),
        ('balance_topup', 'payment'),
        ('topup_amount|yookassa|10000', 'payment'),
        ('menu_referrals', 'referral'),
        ('referral_list', 'referral'),
        ('subscription_connect', 'connect'),
        ('menu_language', 'info'),
        ('admin_panel', None),
        (None, None),
    ],
)
def test_callback_to_banner_key(data, key):
    assert banner_key_for_callback(data) == key


def test_start_command_opens_main():
    assert banner_key_for_message('/start ref_123') == 'main'
    assert banner_key_for_message('/start@ulya_bot') == 'main'
    assert banner_key_for_message('привет') is None


@pytest.fixture
def banners_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(banners, 'BANNERS_DIR', tmp_path)
    monkeypatch.setattr(message_patch, '_banner_file_ids', {})
    return tmp_path


def test_falls_back_to_logo_without_a_file(banners_dir):
    token = set_current_banner('balance')
    try:
        media = message_patch.get_logo_media()
    finally:
        banners._current_banner.reset(token)

    assert getattr(media, 'path', media) != banners_dir / 'balance.png'


def test_uses_banner_file_and_caches_it_per_key(banners_dir):
    (banners_dir / 'balance.jpg').write_bytes(b'jpg')

    class _Photo:
        file_id = 'file-balance'

    class _Result:
        photo = [_Photo()]

    token = set_current_banner('balance')
    try:
        assert message_patch.get_logo_media().path == banners_dir / 'balance.jpg'
        message_patch._cache_logo_file_id(_Result())
        assert message_patch.get_logo_media() == 'file-balance'
    finally:
        banners._current_banner.reset(token)

    # The logo cache is untouched by a banner upload.
    assert message_patch._logo_file_id != 'file-balance'
