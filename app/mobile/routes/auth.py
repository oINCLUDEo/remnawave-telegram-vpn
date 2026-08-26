"""Mobile Telegram authentication routes.

New flow (bot deep-link):
  1. App calls  POST /mobile/v1/auth/init
     → backend creates a one-time token in Redis, returns a ``tg://`` deep link.
  2. App opens the deep link — Telegram opens the bot and automatically sends
     ``/start mobile_auth_<token>``.
  3. The bot's /start handler (app/handlers/start.py) calls
     ``verify_auth_token(token, ...)`` to mark the token as verified.
  4. App polls  GET /mobile/v1/auth/check/{token}  every few seconds.
  5. On "verified" the backend resolves the user from DB and returns
     subscription URL + user info.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.mobile.auth_cache import TOKEN_TTL_SECONDS, create_auth_token, delete_auth_token, get_auth_token
from app.mobile.schemas.auth import (
    MobileAuthCheckResponse,
    MobileAuthInitResponse,
    MobileAuthResponse,
    MobileAuthUserInfo,
)


logger = structlog.get_logger(__name__)

router = APIRouter()

# ── Deep-link prefix used by the bot /start handler ─────────────────────────
MOBILE_AUTH_START_PREFIX = 'mobile_auth_'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_user_data(
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
) -> MobileAuthResponse:
    """Look up or create the user in the DB and return full auth response."""
    try:
        import hashlib

        from app.cabinet.auth.jwt_handler import (
            create_access_token,
            create_refresh_token,
            get_refresh_token_expires_at,
        )
        from app.database.crud.rbac import UserRoleCRUD
        from app.database.crud.user import create_user, get_user_by_telegram_id
        from app.database.models import CabinetRefreshToken

        db_url = settings.get_database_url()
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

        async with async_session() as db:
            user = await get_user_by_telegram_id(db, telegram_id)
            is_new_user = False

            if not user:
                is_new_user = True
                logger.info('Creating new user from mobile deep-link auth', telegram_id=telegram_id)
                user = await create_user(
                    db=db,
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language='ru',
                )
                await db.commit()

            if user.status != 'active':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Учётная запись заблокирована',
                )

            await db.refresh(user, ['subscriptions'])
            subscription = getattr(user, 'subscription', None)
            subscription_url: str | None = None
            if subscription and getattr(subscription, 'subscription_url', None):
                subscription_url = subscription.subscription_url

            # Issue a Cabinet JWT pair so the mobile app can call /cabinet/*
            # endpoints (referral, subscription) with proper Bearer auth —
            # the deep-link flow is the authoritative proof of telegram_id.
            # Mirrors _create_auth_response in app/cabinet/routes/auth.py.
            access_token: str | None = None
            refresh_token: str | None = None
            expires_in: int | None = None
            try:
                perms, role_names, role_level = await UserRoleCRUD.get_user_permissions(db, user.id)
                access_token = create_access_token(
                    user.id,
                    user.telegram_id,
                    permissions=perms,
                    roles=role_names,
                    role_level=role_level,
                )
                refresh_token = create_refresh_token(user.id)
                expires_in = settings.get_cabinet_access_token_expire_minutes() * 60
                db.add(
                    CabinetRefreshToken(
                        user_id=user.id,
                        token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
                        device_info='mobile-app',
                        expires_at=get_refresh_token_expires_at(),
                    )
                )
                await db.commit()
            except Exception as exc:  # noqa: BLE001 — tokens are an enhancement, not a hard dependency
                logger.error('Failed to issue cabinet tokens for mobile auth', error=exc)
                access_token = None
                refresh_token = None
                expires_in = None

        await engine.dispose()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile auth DB error', error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при обращении к базе данных',
        ) from exc

    return MobileAuthResponse(
        subscription_url=subscription_url,
        user=MobileAuthUserInfo(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        ),
        is_new_user=is_new_user,
        has_subscription=bool(subscription_url),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    '/init',
    response_model=MobileAuthInitResponse,
    summary='Инициализировать авторизацию через Telegram-бот',
    description=(
        'Генерирует одноразовый токен, сохраняет его в Redis и возвращает '
        'deep-link для открытия Telegram. '
        'Клиент должен открыть deep_link, после чего пользователь попадёт '
        'в бот и отправит команду /start с токеном.'
    ),
    tags=['mobile'],
)
async def auth_init() -> MobileAuthInitResponse:
    """Create a pending auth token and return the Telegram deep-link."""
    bot_username = settings.get_bot_username()
    if not bot_username:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Бот не настроен. Установите BOT_USERNAME в конфигурации.',
        )

    try:
        token = await create_auth_token()
    except Exception as exc:
        logger.error('Failed to create mobile auth token', error=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Не удалось создать токен авторизации. Попробуйте позже.',
        ) from exc

    start_param = f'{MOBILE_AUTH_START_PREFIX}{token}'
    deep_link = f'tg://resolve?domain={bot_username}&start={start_param}'

    return MobileAuthInitResponse(
        token=token,
        deep_link=deep_link,
        expires_in=TOKEN_TTL_SECONDS,
    )


@router.get(
    '/check/{token}',
    response_model=MobileAuthCheckResponse,
    summary='Проверить статус авторизации',
    description=(
        'Опрашивает Redis на предмет подтверждения токена ботом. '
        'Возвращает status="pending" пока пользователь не открыл бот, '
        'status="verified" после подтверждения, status="expired" если истёк TTL.'
    ),
    tags=['mobile'],
)
async def auth_check(
    token: str = Path(..., description='Токен, полученный из /auth/init', min_length=32, max_length=64),
) -> MobileAuthCheckResponse:
    """Poll the token status.  On "verified" resolves user from DB."""
    data = await get_auth_token(token)

    if data is None:
        return MobileAuthCheckResponse(status='expired')

    token_status = data.get('status', 'pending')

    if token_status == 'pending':
        return MobileAuthCheckResponse(status='pending')

    if token_status == 'verified':
        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return MobileAuthCheckResponse(status='pending')

        auth_response = await _resolve_user_data(
            telegram_id=int(telegram_id),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name'),
            username=data.get('username'),
        )

        # Consume the token so it cannot be replayed.
        await delete_auth_token(token)

        return MobileAuthCheckResponse(status='verified', auth=auth_response)

    return MobileAuthCheckResponse(status='expired')
