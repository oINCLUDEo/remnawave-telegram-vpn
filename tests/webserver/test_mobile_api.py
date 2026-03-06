"""Tests for the mobile API server-list endpoint."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import settings
from app.services.payment_service import PaymentService
from app.webserver.unified_app import create_unified_app


def _make_app(monkeypatch: pytest.MonkeyPatch):
    bot = AsyncMock()
    dispatcher = SimpleNamespace(feed_update=AsyncMock())
    payment_service = AsyncMock(spec=PaymentService)

    monkeypatch.setattr(settings, 'WEB_API_ENABLED', False, raising=False)

    return create_unified_app(
        bot,
        dispatcher,  # type: ignore[arg-type]
        payment_service,
        enable_telegram_webhook=False,
    )


def _make_server(
    squad_uuid: str = 'abc-123',
    display_name: str = 'Germany',
    original_name: str | None = 'de-node-1',
    country_code: str | None = 'DE',
    current_users: int = 42,
    is_available: bool = True,
    description: str | None = 'Test server',
) -> MagicMock:
    server = MagicMock()
    server.squad_uuid = squad_uuid
    server.display_name = display_name
    server.original_name = original_name
    server.country_code = country_code
    server.current_users = current_users
    server.is_available = is_available
    server.description = description
    return server


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_mobile_servers_route_is_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _make_app(monkeypatch)
    paths = {getattr(r, 'path', None) for r in app.routes}
    assert '/mobile/v1/servers' in paths


# ---------------------------------------------------------------------------
# Endpoint logic
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_mobile_servers_returns_available_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Endpoint returns only is_available servers mapped to the Flutter schema."""
    from app.mobile_api.routes.servers import list_mobile_servers

    server = _make_server()

    # Build a mock async DB session whose execute().scalars().all() returns [server].
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [server]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=execute_result)

    result = await list_mobile_servers(db=db_mock)

    assert len(result) == 1
    item = result[0]
    assert item.uuid == 'abc-123'
    assert item.name == 'Germany'
    assert item.address == 'de-node-1'
    assert item.country_code == 'DE'
    assert item.users_online == 42
    assert item.is_connected is False
    assert item.is_disabled is True
    assert item.link is None
    assert item.protocol == 'vless'
    assert item.description == 'Test server'


@pytest.mark.anyio
async def test_list_mobile_servers_empty_when_no_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Endpoint returns an empty list when no servers exist."""
    from app.mobile_api.routes.servers import list_mobile_servers

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=execute_result)

    result = await list_mobile_servers(db=db_mock)

    assert result == []


@pytest.mark.anyio
async def test_list_mobile_servers_address_falls_back_to_display_name() -> None:
    """When original_name is None, address falls back to display_name."""
    from app.mobile_api.routes.servers import list_mobile_servers

    server = _make_server(original_name=None, display_name='Netherlands')

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [server]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=execute_result)

    result = await list_mobile_servers(db=db_mock)

    assert len(result) == 1
    assert result[0].address == 'Netherlands'


@pytest.mark.anyio
async def test_list_mobile_servers_link_always_null() -> None:
    """The link field must always be None regardless of the server data."""
    from app.mobile_api.routes.servers import list_mobile_servers

    server = _make_server()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [server]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=execute_result)

    result = await list_mobile_servers(db=db_mock)

    for item in result:
        assert item.link is None


@pytest.mark.anyio
async def test_list_mobile_servers_is_disabled_always_true() -> None:
    """isDisabled must always be True (servers are visible but not connectable)."""
    from app.mobile_api.routes.servers import list_mobile_servers

    server = _make_server()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [server]
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=execute_result)

    result = await list_mobile_servers(db=db_mock)

    for item in result:
        assert item.is_disabled is True
