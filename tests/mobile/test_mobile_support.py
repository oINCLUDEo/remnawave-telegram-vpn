"""Tests for the mobile /support/tickets endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(status: str = 'active', user_id: int = 42, telegram_id: int = 111222333):
    user = MagicMock()
    user.status = status
    user.telegram_id = telegram_id
    user.id = user_id
    return user


def _make_ticket(ticket_id: int = 1, user_id: int = 42, status: str = 'open'):
    ticket = MagicMock()
    ticket.id = ticket_id
    ticket.user_id = user_id
    ticket.title = 'Test ticket'
    ticket.status = status
    ticket.priority = 'normal'
    ticket.is_user_reply_blocked = False
    from datetime import UTC, datetime
    ticket.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    ticket.updated_at = datetime(2024, 1, 2, tzinfo=UTC)
    return ticket


def _make_message(msg_id: int = 10, ticket_id: int = 1, is_from_admin: bool = False):
    msg = MagicMock()
    msg.id = msg_id
    msg.ticket_id = ticket_id
    msg.message_text = 'Hello'
    msg.is_from_admin = is_from_admin
    from datetime import UTC, datetime
    msg.created_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return msg


def _db_ctx():
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_session_class = MagicMock(return_value=mock_db)
    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()
    return mock_db, mock_session_class, mock_engine


# ---------------------------------------------------------------------------
# Tests — GET /support/tickets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tickets_returns_empty_list():
    from app.mobile.routes.support import list_tickets

    mock_db, mock_session_class, mock_engine = _db_ctx()

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.get_user_tickets = AsyncMock(return_value=[])

        result = await list_tickets(x_telegram_id=111222333)

    assert result.tickets == []


@pytest.mark.asyncio
async def test_list_tickets_returns_tickets():
    from app.mobile.routes.support import list_tickets

    mock_db, mock_session_class, mock_engine = _db_ctx()
    ticket = _make_ticket()

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.get_user_tickets = AsyncMock(return_value=[ticket])

        result = await list_tickets(x_telegram_id=111222333)

    assert len(result.tickets) == 1
    assert result.tickets[0].id == 1
    assert result.tickets[0].status == 'open'


# ---------------------------------------------------------------------------
# Tests — POST /support/tickets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_ticket_success():
    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    mock_db, mock_session_class, mock_engine = _db_ctx()
    ticket = _make_ticket()

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.count_user_tickets_by_statuses = AsyncMock(return_value=0)
        mock_crud.create_ticket = AsyncMock(return_value=ticket)

        body = MobileCreateTicketRequest(title='My issue', message='Details here')
        result = await create_ticket(body=body, x_telegram_id=111222333)

    assert result.id == ticket.id
    assert result.status == 'open'


@pytest.mark.asyncio
async def test_create_ticket_rejects_empty_title():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    body = MobileCreateTicketRequest(title='', message='Some text')

    with pytest.raises(HTTPException) as exc_info:
        await create_ticket(body=body, x_telegram_id=111222333)

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_rejects_empty_message():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    body = MobileCreateTicketRequest(title='Valid title', message='')

    with pytest.raises(HTTPException) as exc_info:
        await create_ticket(body=body, x_telegram_id=111222333)

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_limits_open_tickets():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    mock_db, mock_session_class, mock_engine = _db_ctx()

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.count_user_tickets_by_statuses = AsyncMock(return_value=5)

        body = MobileCreateTicketRequest(title='Another issue', message='Text')
        with pytest.raises(HTTPException) as exc_info:
            await create_ticket(body=body, x_telegram_id=111222333)

    assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Tests — GET /support/tickets/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ticket_returns_detail():
    from app.mobile.routes.support import get_ticket

    mock_db, mock_session_class, mock_engine = _db_ctx()
    ticket = _make_ticket()
    msg = _make_message()

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
        patch('app.mobile.routes.support.TicketMessageCRUD') as mock_msg_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)
        mock_msg_crud.get_ticket_messages = AsyncMock(return_value=[msg])

        result = await get_ticket(ticket_id=1, x_telegram_id=111222333)

    assert result.id == 1
    assert len(result.messages) == 1
    assert result.messages[0].is_from_admin is False


@pytest.mark.asyncio
async def test_get_ticket_returns_404_wrong_owner():
    from fastapi import HTTPException

    from app.mobile.routes.support import get_ticket

    mock_db, mock_session_class, mock_engine = _db_ctx()
    # ticket belongs to user_id=99, but logged in as user_id=42
    ticket = _make_ticket(user_id=99)

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user(user_id=42)),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)

        with pytest.raises(HTTPException) as exc_info:
            await get_ticket(ticket_id=1, x_telegram_id=111222333)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests — POST /support/tickets/{id}/messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reply_to_ticket_success():
    from app.mobile.routes.support import MobileReplyRequest, reply_to_ticket

    mock_db, mock_session_class, mock_engine = _db_ctx()
    ticket = _make_ticket()
    msg = _make_message()

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
        patch('app.mobile.routes.support.TicketMessageCRUD') as mock_msg_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)
        mock_msg_crud.add_message = AsyncMock(return_value=msg)

        body = MobileReplyRequest(message='My reply')
        result = await reply_to_ticket(body=body, ticket_id=1, x_telegram_id=111222333)

    assert result.id == msg.id
    assert result.is_from_admin is False


@pytest.mark.asyncio
async def test_reply_to_closed_ticket_returns_409():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileReplyRequest, reply_to_ticket

    mock_db, mock_session_class, mock_engine = _db_ctx()
    ticket = _make_ticket(status='closed')

    with (
        patch('app.mobile.routes.support.settings') as mock_settings,
        patch('app.mobile.routes.support.create_async_engine', return_value=mock_engine),
        patch('app.mobile.routes.support.sessionmaker', return_value=mock_session_class),
        patch('app.mobile.routes.support.get_user_by_telegram_id',
              new_callable=AsyncMock, return_value=_make_user()),
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
    ):
        mock_settings.get_database_url.return_value = 'sqlite+aiosqlite://'
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)

        body = MobileReplyRequest(message='Response text')
        with pytest.raises(HTTPException) as exc_info:
            await reply_to_ticket(body=body, ticket_id=1, x_telegram_id=111222333)

    assert exc_info.value.status_code == 409
