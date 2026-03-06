from __future__ import annotations

from pydantic import BaseModel, Field


class MobileServerResponse(BaseModel):
    """Модель сервера для Flutter-клиента."""

    uuid: str
    name: str
    address: str
    countryCode: str
    isConnected: bool = False
    isDisabled: bool = True
    usersOnline: int = 0
    link: None = Field(default=None)
    protocol: str
    description: str | None = None


class MobileServerListResponse(BaseModel):
    """Список серверов для Flutter-клиента."""

    servers: list[MobileServerResponse]
    total: int
