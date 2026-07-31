"""Pydantic schema for the mobile remote-config response."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MobileRemoteConfigResponse(BaseModel):
    """Backend-driven configuration for the Flutter client.

    Sourced from the generic admin settings system (``Settings`` fields
    prefixed ``MOBILE_``) — changes made via the admin API/panel apply
    immediately, with no app store release required.
    """

    schema_version: int = Field(1, description='Bump when the response shape changes incompatibly')

    min_supported_build: int = Field(..., description='Below this build number the client must update')
    latest_build: int = Field(..., description='Latest available build — used for a soft "update available" hint')
    force_update: bool = Field(..., description='When true, the client blocks usage below min_supported_build')
    update_url: str | None = Field(None, description='Store/download link for the running platform (android/ios)')

    maintenance_enabled: bool = Field(..., description='Mobile-app-specific maintenance banner/gate')
    maintenance_message: str = Field('', description='Message shown while maintenance_enabled is true')

    blocked_apps_default: list[str] = Field(
        default_factory=list,
        description='Default split-tunneling exclusion list seeded on first launch',
    )
