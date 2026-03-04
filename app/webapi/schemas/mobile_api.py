"""Pydantic-схемы для публичного мобильного API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MobileServerResponse(BaseModel):
    """Информация о сервере для мобильного клиента Flutter.

    Серверы возвращаются в режиме публичного каталога:
    ``link`` всегда ``null``, ``isDisabled`` всегда ``true`` —
    сервера видны, но подключение не предоставляется.
    """

    model_config = ConfigDict(populate_by_name=True)

    uuid: str
    name: str
    address: str | None = None
    country_code: str | None = Field(default=None, alias='countryCode')
    is_connected: bool = Field(alias='isConnected')
    is_disabled: bool = Field(alias='isDisabled')
    users_online: int = Field(alias='usersOnline')
    link: None = None
    protocol: str | None = None
    description: str | None = None


class MobileServerListResponse(BaseModel):
    """Список публичных серверов для мобильного клиента."""

    model_config = ConfigDict(populate_by_name=True)

    servers: list[MobileServerResponse]
