"""Pydantic schemas for the mobile server-list endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MobileServerItem(BaseModel):
    """Single server entry compatible with the Flutter client model."""

    model_config = ConfigDict(populate_by_name=True)

    uuid: str
    name: str
    address: str | None = None
    country_code: str | None = Field(default=None, alias='countryCode')
    is_connected: bool = Field(False, alias='isConnected')
    is_disabled: bool = Field(True, alias='isDisabled')
    users_online: int = Field(0, alias='usersOnline')
    link: None = None
    protocol: str = 'vless'
    description: str | None = None
