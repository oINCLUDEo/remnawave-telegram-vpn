"""Mobile support ticket endpoints.

Allows authenticated mobile users to:
  GET  /mobile/v1/support/tickets           — list own tickets
  POST /mobile/v1/support/tickets           — create a ticket
  GET  /mobile/v1/support/tickets/{id}      — get a ticket with messages
  POST /mobile/v1/support/tickets/{id}/messages — reply to a ticket
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.crud.ticket import TicketCRUD, TicketMessageCRUD
from app.database.crud.user import get_user_by_telegram_id
from app.database.models import TicketStatus
from app.mobile.schemas.support import (
    MobileCreateTicketRequest,
    MobileReplyRequest,
    MobileTicketDetailResponse,
    MobileTicketListResponse,
    MobileTicketMessageResponse,
    MobileTicketResponse,
)


logger = structlog.get_logger(__name__)

router = APIRouter()

_MAX_OPEN_TICKETS = 5
_MAX_TITLE_LEN = 200
_MAX_MESSAGE_LEN = 4000


# ── Helper ────────────────────────────────────────────────────────────────────


async def _get_user_or_raise(db: AsyncSession, telegram_id: int):
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Пользователь не найден')
    if getattr(user, 'status', 'active') != 'active':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Учётная запись заблокирована')
    return user


def _make_session_factory(db_url: str):
    engine = create_async_engine(db_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
    return engine, factory


def _ticket_to_response(ticket) -> MobileTicketResponse:
    return MobileTicketResponse(
        id=ticket.id,
        title=ticket.title,
        status=ticket.status,
        priority=ticket.priority,
        created_at=int(ticket.created_at.timestamp()) if ticket.created_at else 0,
        updated_at=int(ticket.updated_at.timestamp()) if ticket.updated_at else 0,
    )


def _message_to_response(msg) -> MobileTicketMessageResponse:
    return MobileTicketMessageResponse(
        id=msg.id,
        message_text=msg.message_text,
        is_from_admin=msg.is_from_admin,
        created_at=int(msg.created_at.timestamp()) if msg.created_at else 0,
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get(
    '/tickets',
    response_model=MobileTicketListResponse,
    summary='Список тикетов пользователя',
    tags=['mobile'],
)
async def list_tickets(
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> MobileTicketListResponse:
    """Return all tickets belonging to the authenticated user."""
    db_url = settings.get_database_url()
    engine, factory = _make_session_factory(db_url)
    try:
        async with factory() as db:
            user = await _get_user_or_raise(db, x_telegram_id)
            tickets = await TicketCRUD.get_user_tickets(db, user.id, limit=50)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile GET /support/tickets error', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Ошибка базы данных') from exc
    finally:
        await engine.dispose()

    return MobileTicketListResponse(tickets=[_ticket_to_response(t) for t in tickets])


@router.post(
    '/tickets',
    response_model=MobileTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создать тикет',
    tags=['mobile'],
)
async def create_ticket(
    body: MobileCreateTicketRequest,
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> MobileTicketResponse:
    """Create a new support ticket."""
    title = (body.title or '').strip()
    message_text = (body.message or '').strip()

    # Append diagnostic logs to the message text if provided
    if body.logs:
        logs_text = body.logs.strip()
        if logs_text:
            _MAX_LOGS_LEN = 8000
            if len(logs_text) > _MAX_LOGS_LEN:
                logs_text = logs_text[-_MAX_LOGS_LEN:]
            message_text = f'{message_text}\n\n--- Диагностические логи ---\n{logs_text}'

    if not title:
        raise HTTPException(status_code=422, detail='Укажите тему обращения')
    if len(title) > _MAX_TITLE_LEN:
        raise HTTPException(status_code=422, detail='Тема слишком длинная')
    if not message_text:
        raise HTTPException(status_code=422, detail='Укажите текст сообщения')
    if len(message_text) > _MAX_MESSAGE_LEN:
        raise HTTPException(status_code=422, detail='Сообщение слишком длинное')

    db_url = settings.get_database_url()
    engine, factory = _make_session_factory(db_url)
    try:
        async with factory() as db:
            user = await _get_user_or_raise(db, x_telegram_id)

            # Limit concurrent open tickets per user
            open_count = await TicketCRUD.count_user_tickets_by_statuses(
                db, user.id, [TicketStatus.OPEN.value, TicketStatus.ANSWERED.value, TicketStatus.PENDING.value]
            )
            if open_count >= _MAX_OPEN_TICKETS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f'Максимальное количество открытых тикетов: {_MAX_OPEN_TICKETS}',
                )

            ticket = await TicketCRUD.create_ticket(
                db,
                user_id=user.id,
                title=title,
                message_text=message_text,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile POST /support/tickets error', telegram_id=x_telegram_id, error=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Ошибка базы данных') from exc
    finally:
        await engine.dispose()

    return _ticket_to_response(ticket)


@router.get(
    '/tickets/{ticket_id}',
    response_model=MobileTicketDetailResponse,
    summary='Детали тикета с сообщениями',
    tags=['mobile'],
)
async def get_ticket(
    ticket_id: int = Path(..., gt=0),
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> MobileTicketDetailResponse:
    """Return a ticket with its messages."""
    db_url = settings.get_database_url()
    engine, factory = _make_session_factory(db_url)
    try:
        async with factory() as db:
            user = await _get_user_or_raise(db, x_telegram_id)
            ticket = await TicketCRUD.get_ticket_by_id(db, ticket_id, load_messages=True)
            if not ticket or ticket.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Тикет не найден')
            messages = await TicketMessageCRUD.get_ticket_messages(db, ticket_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile GET /support/tickets/{id} error', ticket_id=ticket_id, error=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Ошибка базы данных') from exc
    finally:
        await engine.dispose()

    return MobileTicketDetailResponse(
        **_ticket_to_response(ticket).model_dump(),
        messages=[_message_to_response(m) for m in messages],
    )


@router.post(
    '/tickets/{ticket_id}/messages',
    response_model=MobileTicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Ответить в тикет',
    tags=['mobile'],
)
async def reply_to_ticket(
    body: MobileReplyRequest,
    ticket_id: int = Path(..., gt=0),
    x_telegram_id: int = Header(..., alias='X-Telegram-Id'),
) -> MobileTicketMessageResponse:
    """Add a user reply to an existing ticket."""
    message_text = (body.message or '').strip()
    if not message_text:
        raise HTTPException(status_code=422, detail='Укажите текст сообщения')
    if len(message_text) > _MAX_MESSAGE_LEN:
        raise HTTPException(status_code=422, detail='Сообщение слишком длинное')

    db_url = settings.get_database_url()
    engine, factory = _make_session_factory(db_url)
    try:
        async with factory() as db:
            user = await _get_user_or_raise(db, x_telegram_id)
            ticket = await TicketCRUD.get_ticket_by_id(db, ticket_id, load_messages=False)
            if not ticket or ticket.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Тикет не найден')
            if ticket.status == TicketStatus.CLOSED.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail='Тикет закрыт. Создайте новое обращение.'
                )
            if ticket.is_user_reply_blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail='Ответы в этот тикет заблокированы'
                )
            msg = await TicketMessageCRUD.add_message(
                db, ticket_id=ticket_id, user_id=user.id, message_text=message_text
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile POST /support/tickets/{id}/messages error', ticket_id=ticket_id, error=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Ошибка базы данных') from exc
    finally:
        await engine.dispose()

    return _message_to_response(msg)
