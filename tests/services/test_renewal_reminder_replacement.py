"""Новое напоминание о продлении убирает предыдущее (MonitoringService._replace_renewal_reminder)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from app.config import settings
from app.services import monitoring_service as ms


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, expire=None) -> bool:
        self.store[key] = value
        return True


def sent(message_id: int):
    return SimpleNamespace(chat=SimpleNamespace(id=777), message_id=message_id)


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ms, 'cache', FakeCache())
    monkeypatch.setattr(settings, 'NOTIFICATIONS_REPLACE_PREVIOUS_REMINDER', True, raising=False)
    bot = SimpleNamespace(delete_message=AsyncMock(), edit_message_reply_markup=AsyncMock())
    return ms.MonitoringService(bot=bot)


USER = SimpleNamespace(id=1)
SUB = SimpleNamespace(id=10)


async def test_first_reminder_only_remembered(service) -> None:
    await service._replace_renewal_reminder(USER, SUB, sent(100))

    service.bot.delete_message.assert_not_awaited()
    assert ms.cache.store['renewal_reminder:1:10'] == {'chat_id': 777, 'message_id': 100}


async def test_next_reminder_deletes_previous(service) -> None:
    await service._replace_renewal_reminder(USER, SUB, sent(100))
    await service._replace_renewal_reminder(USER, SUB, sent(101))

    service.bot.delete_message.assert_awaited_once_with(chat_id=777, message_id=100)
    service.bot.edit_message_reply_markup.assert_not_awaited()
    assert ms.cache.store['renewal_reminder:1:10']['message_id'] == 101


async def test_too_old_to_delete_loses_buttons(service) -> None:
    service.bot.delete_message.side_effect = TelegramBadRequest(method=None, message="message can't be deleted")
    await service._replace_renewal_reminder(USER, SUB, sent(100))
    await service._replace_renewal_reminder(USER, SUB, sent(101))

    service.bot.edit_message_reply_markup.assert_awaited_once_with(chat_id=777, message_id=100, reply_markup=None)


async def test_failed_send_keeps_previous(service) -> None:
    await service._replace_renewal_reminder(USER, SUB, sent(100))
    await service._replace_renewal_reminder(USER, SUB, None)

    service.bot.delete_message.assert_not_awaited()
    assert ms.cache.store['renewal_reminder:1:10']['message_id'] == 100


async def test_switch_off(service, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, 'NOTIFICATIONS_REPLACE_PREVIOUS_REMINDER', False, raising=False)
    await service._replace_renewal_reminder(USER, SUB, sent(100))
    assert ms.cache.store == {}
