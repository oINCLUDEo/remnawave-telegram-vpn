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
    msg.has_media = False
    msg.media_type = None
    from datetime import UTC, datetime
    msg.created_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return msg


def _mock_db():
    """Opaque placeholder — TicketCRUD/TicketMessageCRUD are mocked wholesale
    in every test below, so this is never actually touched, just passed
    through as the first positional arg."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# Tests — GET /support/tickets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tickets_returns_empty_list():
    from app.mobile.routes.support import list_tickets

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_user_tickets = AsyncMock(return_value=[])
        result = await list_tickets(user=_make_user(), db=_mock_db())

    assert result.tickets == []


@pytest.mark.asyncio
async def test_list_tickets_returns_tickets():
    from app.mobile.routes.support import list_tickets

    ticket = _make_ticket()

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_user_tickets = AsyncMock(return_value=[ticket])
        result = await list_tickets(user=_make_user(), db=_mock_db())

    assert len(result.tickets) == 1
    assert result.tickets[0].id == 1
    assert result.tickets[0].status == 'open'


# ---------------------------------------------------------------------------
# Tests — POST /support/tickets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_ticket_success():
    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    ticket = _make_ticket()

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.count_user_tickets_by_statuses = AsyncMock(return_value=0)
        mock_crud.create_ticket = AsyncMock(return_value=ticket)

        body = MobileCreateTicketRequest(title='My issue', message='Details here')
        result = await create_ticket(body=body, user=_make_user(), db=_mock_db())

    assert result.id == ticket.id
    assert result.status == 'open'


@pytest.mark.asyncio
async def test_create_ticket_rejects_empty_title():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    body = MobileCreateTicketRequest(title='', message='Some text')

    with pytest.raises(HTTPException) as exc_info:
        await create_ticket(body=body, user=_make_user(), db=_mock_db())

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_rejects_empty_message():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    body = MobileCreateTicketRequest(title='Valid title', message='')

    with pytest.raises(HTTPException) as exc_info:
        await create_ticket(body=body, user=_make_user(), db=_mock_db())

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_limits_open_tickets():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.count_user_tickets_by_statuses = AsyncMock(return_value=5)

        body = MobileCreateTicketRequest(title='Another issue', message='Text')
        with pytest.raises(HTTPException) as exc_info:
            await create_ticket(body=body, user=_make_user(), db=_mock_db())

    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_create_ticket_with_long_logs_does_not_return_422():
    """Logs are stored as a file attachment, never appended to message_text.

    A ticket with very long diagnostic logs must succeed regardless of log size.
    """
    from app.mobile.routes.support import MobileCreateTicketRequest, create_ticket

    ticket = _make_ticket()
    # Build a log payload that would previously exceed _MAX_MESSAGE_LEN when combined
    long_logs = 'LOG LINE\n' * 1000  # ~9 000 chars

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.count_user_tickets_by_statuses = AsyncMock(return_value=0)
        mock_crud.create_ticket = AsyncMock(return_value=ticket)

        body = MobileCreateTicketRequest(
            title='Bug report',
            message='Short user message',
            logs=long_logs,
        )
        result = await create_ticket(body=body, user=_make_user(), db=_mock_db())

    assert result.id == ticket.id


# ---------------------------------------------------------------------------
# Tests — GET /support/tickets/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ticket_returns_detail():
    from app.mobile.routes.support import get_ticket

    ticket = _make_ticket()
    msg = _make_message()

    with (
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
        patch('app.mobile.routes.support.TicketMessageCRUD') as mock_msg_crud,
    ):
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)
        mock_msg_crud.get_ticket_messages = AsyncMock(return_value=[msg])

        result = await get_ticket(ticket_id=1, user=_make_user(), db=_mock_db())

    assert result.id == 1
    assert len(result.messages) == 1
    assert result.messages[0].is_from_admin is False


@pytest.mark.asyncio
async def test_get_ticket_returns_404_wrong_owner():
    from fastapi import HTTPException

    from app.mobile.routes.support import get_ticket

    # ticket belongs to user_id=99, but logged in as user_id=42
    ticket = _make_ticket(user_id=99)

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)

        with pytest.raises(HTTPException) as exc_info:
            await get_ticket(ticket_id=1, user=_make_user(user_id=42), db=_mock_db())

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tests — POST /support/tickets/{id}/messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reply_to_ticket_success():
    from app.mobile.routes.support import MobileReplyRequest, reply_to_ticket

    ticket = _make_ticket()
    msg = _make_message()

    with (
        patch('app.mobile.routes.support.TicketCRUD') as mock_crud,
        patch('app.mobile.routes.support.TicketMessageCRUD') as mock_msg_crud,
    ):
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)
        mock_msg_crud.add_message = AsyncMock(return_value=msg)

        body = MobileReplyRequest(message='My reply')
        result = await reply_to_ticket(body=body, ticket_id=1, user=_make_user(), db=_mock_db())

    assert result.id == msg.id
    assert result.is_from_admin is False


@pytest.mark.asyncio
async def test_reply_to_closed_ticket_returns_409():
    from fastapi import HTTPException

    from app.mobile.routes.support import MobileReplyRequest, reply_to_ticket

    ticket = _make_ticket(status='closed')

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)

        body = MobileReplyRequest(message='Response text')
        with pytest.raises(HTTPException) as exc_info:
            await reply_to_ticket(body=body, ticket_id=1, user=_make_user(), db=_mock_db())

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Tests — POST /support/tickets/{id}/close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_ticket_success():
    from app.mobile.routes.support import close_ticket

    ticket = _make_ticket(status='open')

    async def _fake_close(db, tid):
        ticket.status = 'closed'
        return True

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)
        mock_crud.close_ticket = AsyncMock(side_effect=_fake_close)

        result = await close_ticket(ticket_id=1, user=_make_user(), db=_mock_db())

    assert result.id == ticket.id
    assert result.status == 'closed'


@pytest.mark.asyncio
async def test_close_ticket_already_closed_returns_409():
    from fastapi import HTTPException

    from app.mobile.routes.support import close_ticket

    ticket = _make_ticket(status='closed')

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)

        with pytest.raises(HTTPException) as exc_info:
            await close_ticket(ticket_id=1, user=_make_user(), db=_mock_db())

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_close_ticket_wrong_owner_returns_404():
    from fastapi import HTTPException

    from app.mobile.routes.support import close_ticket

    # Ticket belongs to user_id=99, not user_id=42
    ticket = _make_ticket(ticket_id=1, user_id=99, status='open')

    with patch('app.mobile.routes.support.TicketCRUD') as mock_crud:
        mock_crud.get_ticket_by_id = AsyncMock(return_value=ticket)

        with pytest.raises(HTTPException) as exc_info:
            await close_ticket(ticket_id=1, user=_make_user(user_id=42), db=_mock_db())

    assert exc_info.value.status_code == 404
