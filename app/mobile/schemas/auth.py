from __future__ import annotations

from pydantic import BaseModel, Field


class MobileAuthUserInfo(BaseModel):
    """Minimal user info returned after successful authentication."""

    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None


class MobileAuthResponse(BaseModel):
    """Response returned after a confirmed auth token poll."""

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


class MobileAuthInitResponse(BaseModel):
    """Response from the auth/init endpoint."""

    token: str = Field(..., description='One-time auth token (UUID)')
    deep_link: str = Field(
        ...,
        description='Telegram deep-link the client should open (tg:// scheme or https://t.me/…)',
    )
    expires_in: int = Field(..., description='Token TTL in seconds')


class MobileAuthCheckResponse(BaseModel):
    """Response from the auth/check/{token} endpoint."""

    status: str = Field(
        ...,
        description='"pending" while waiting, "verified" after user opened the bot, "expired" when TTL elapsed',
    )
    auth: MobileAuthResponse | None = Field(
        None,
        description='Populated only when status == "verified"',
    )
