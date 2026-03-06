from __future__ import annotations

from pydantic import BaseModel, Field


class MobileTelegramWidgetAuthRequest(BaseModel):
    """Request for mobile Telegram Login Widget authentication.

    The fields mirror the object returned by the Telegram Login Widget
    JavaScript callback (https://core.telegram.org/widgets/login).
    """

    id: int = Field(..., description='Telegram user ID')
    first_name: str = Field(..., description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    username: str | None = Field(None, description="User's Telegram username")
    photo_url: str | None = Field(None, description="URL to user's profile photo")
    auth_date: int = Field(..., description='Unix timestamp of the authentication')
    hash: str = Field(..., description='HMAC-SHA256 signature from Telegram')


class MobileAuthUserInfo(BaseModel):
    """Minimal user info returned after successful authentication."""

    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None


class MobileAuthResponse(BaseModel):
    """Response returned after successful Telegram authentication."""

    subscription_url: str | None = Field(
        None,
        description=(
            'Personal subscription URL. Present only when the user already has an active subscription in the service.'
        ),
    )
    user: MobileAuthUserInfo
    is_new_user: bool = Field(
        False,
        description='True when the account was created during this auth request.',
    )
    has_subscription: bool = Field(
        False,
        description='True when subscription_url is available.',
    )
