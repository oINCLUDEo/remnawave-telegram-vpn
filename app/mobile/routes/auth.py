from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.mobile.schemas.auth import MobileAuthResponse, MobileAuthUserInfo, MobileTelegramWidgetAuthRequest


logger = structlog.get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_telegram_widget_data(data: dict[str, Any], bot_token: str, max_age_seconds: int = 86400) -> bool:
    """Validate Telegram Login Widget auth data using the given bot token.

    The algorithm is documented at https://core.telegram.org/widgets/login.
    """
    auth_data = {k: v for k, v in data.items() if v is not None}
    check_hash = auth_data.pop('hash', None)
    if not check_hash:
        return False

    auth_date = auth_data.get('auth_date')
    if auth_date:
        try:
            auth_time = datetime.fromtimestamp(int(auth_date), tz=UTC)
            age = (datetime.now(UTC) - auth_time).total_seconds()
            if age > max_age_seconds:
                return False
        except (ValueError, TypeError, OSError):
            return False

    data_check_arr = [f'{k}={v}' for k, v in sorted(auth_data.items())]
    data_check_string = '\n'.join(data_check_arr)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(calculated_hash, check_hash)


async def _get_or_create_user(
    db: AsyncSession,
    request: MobileTelegramWidgetAuthRequest,
) -> tuple[Any, bool]:
    """Return (user, is_new_user).  Raises HTTPException on blocked user."""
    from app.database.crud.user import create_user, get_user_by_telegram_id

    user = await get_user_by_telegram_id(db, request.id)
    is_new_user = False

    if not user:
        is_new_user = True
        logger.info(
            'Creating new user from mobile auth',
            telegram_id=request.id,
            username=request.username,
        )
        user = await create_user(
            db=db,
            telegram_id=request.id,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            language='ru',
        )
        await db.commit()

    if user.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Учётная запись заблокирована',
        )

    return user, is_new_user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    '/widget-page',
    response_class=HTMLResponse,
    summary='Страница Telegram Login Widget',
    description=(
        'Возвращает HTML-страницу с кнопкой авторизации через Telegram. '
        'Используется Flutter-клиентом в WebView для получения данных авторизации.'
    ),
    tags=['mobile'],
)
async def get_auth_widget_page() -> HTMLResponse:
    """Serve the Telegram Login Widget HTML page for the Flutter WebView."""
    bot_username = settings.MOBILE_AUTH_BOT_USERNAME or ''
    is_configured = settings.is_mobile_auth_enabled() and bool(bot_username)

    if not is_configured:
        html = _build_error_page(
            'Авторизация не настроена',
            'Администратор ещё не включил мобильную авторизацию через Telegram.',
        )
        return HTMLResponse(content=html, status_code=200)

    html = _build_widget_page(bot_username)
    return HTMLResponse(content=html)


@router.post(
    '/telegram/widget',
    response_model=MobileAuthResponse,
    summary='Авторизация через Telegram Login Widget',
    description=(
        'Принимает данные от Telegram Login Widget, проверяет их подпись '
        'с помощью MOBILE_AUTH_BOT_TOKEN и возвращает URL подписки пользователя.'
    ),
    tags=['mobile'],
)
async def auth_telegram_widget(
    request: MobileTelegramWidgetAuthRequest,
) -> MobileAuthResponse:
    """Authenticate using Telegram Login Widget data and return subscription info."""
    bot_token = settings.get_mobile_auth_bot_token()
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Мобильная авторизация через Telegram не настроена',
        )

    widget_data = request.model_dump(exclude_none=False)
    if not _validate_telegram_widget_data(widget_data, bot_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверные или устаревшие данные авторизации Telegram',
        )

    # Look up or create the user and retrieve subscription URL.
    try:
        db_url = settings.get_database_url()
        engine = create_async_engine(db_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

        async with async_session() as db:
            user, is_new_user = await _get_or_create_user(db, request)

            # Load subscription eagerly so we can read subscription_url.
            await db.refresh(user, ['subscription'])
            subscription = getattr(user, 'subscription', None)
            subscription_url: str | None = None
            if subscription and getattr(subscription, 'subscription_url', None):
                subscription_url = subscription.subscription_url

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
            telegram_id=request.id,
            first_name=request.first_name,
            last_name=request.last_name,
            username=request.username,
        ),
        is_new_user=is_new_user,
        has_subscription=bool(subscription_url),
    )


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _build_widget_page(bot_username: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Войти через Telegram</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0F0F1A;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-family: -apple-system, 'Roboto', sans-serif;
      color: #E6E9EF;
      padding: 24px;
    }}
    .card {{
      background: #171A21;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 24px;
      padding: 36px 28px;
      max-width: 340px;
      width: 100%;
      text-align: center;
    }}
    .icon {{
      width: 64px;
      height: 64px;
      background: rgba(108, 92, 231, 0.15);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px;
      font-size: 32px;
    }}
    h1 {{
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    p {{
      color: #9CA3AF;
      font-size: 14px;
      line-height: 1.6;
      margin-bottom: 28px;
    }}
    .tg-wrapper {{
      display: flex;
      justify-content: center;
    }}
    #status {{
      margin-top: 20px;
      font-size: 14px;
      color: #6C5CE7;
      min-height: 20px;
    }}
    .error {{ color: #E74C3C; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🔐</div>
    <h1>Войти через Telegram</h1>
    <p>Нажмите кнопку ниже, чтобы войти в аккаунт с помощью Telegram.</p>
    <div class="tg-wrapper">
      <script
        async
        src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="{bot_username}"
        data-size="large"
        data-onauth="onTelegramAuth(user)"
        data-request-access="write">
      </script>
    </div>
    <div id="status"></div>
  </div>

  <script>
    function onTelegramAuth(user) {{
      document.getElementById('status').textContent = 'Отправка данных…';
      try {{
        // Send auth data to Flutter via JavaScript channel
        if (window.TelegramAuthChannel) {{
          window.TelegramAuthChannel.postMessage(JSON.stringify(user));
        }} else {{
          // Fallback: post to parent frame
          window.parent.postMessage(JSON.stringify(user), '*');
        }}
      }} catch(e) {{
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = 'Ошибка: ' + e.message;
      }}
    }}
  </script>
</body>
</html>"""


def _build_error_page(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0F0F1A;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-family: -apple-system, 'Roboto', sans-serif;
      color: #9CA3AF;
      padding: 24px;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div>
    <div style="font-size:48px;margin-bottom:16px">⚙️</div>
    <h2 style="color:#E6E9EF;margin-bottom:10px">{title}</h2>
    <p style="font-size:14px;line-height:1.6">{message}</p>
  </div>
</body>
</html>"""
