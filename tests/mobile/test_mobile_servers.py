"""Tests for the mobile API servers endpoint."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from app.external.remnawave_api import RemnaWaveHost
from app.mobile.routes.servers import list_mobile_servers
from app.mobile.schemas.servers import MobileServerListResponse


def _make_host(
    uuid: str = 'abc-123',
    name: str = 'Test Server',
    address: str = '1.2.3.4',
    country_code: str = 'DE',
    is_connected: bool = True,
    is_disabled: bool = False,
    is_hidden: bool = False,
    users_online: int = 5,
    protocol: str = 'vless',
    description: str | None = None,
) -> RemnaWaveHost:
    return RemnaWaveHost(
        uuid=uuid,
        name=name,
        address=address,
        country_code=country_code,
        is_connected=is_connected,
        is_disabled=is_disabled,
        is_hidden=is_hidden,
        users_online=users_online,
        protocol=protocol,
        description=description,
    )


def _make_service(hosts: list[RemnaWaveHost], is_configured: bool = True) -> MagicMock:
    """Creates a mock RemnaWaveService that returns the given hosts."""
    mock_api = AsyncMock()
    mock_api.get_hosts = AsyncMock(return_value=hosts)

    @asynccontextmanager
    async def _get_api_client():
        yield mock_api

    service = MagicMock()
    service.is_configured = is_configured
    service.configuration_error = None
    service.get_api_client = _get_api_client
    return service


async def _call(
    hosts: list[RemnaWaveHost], *, is_configured: bool = True, hidden_uuids: set[str] | None = None
) -> MobileServerListResponse:
    service = _make_service(hosts, is_configured=is_configured)
    with (
        patch('app.mobile.routes.servers.RemnaWaveService', return_value=service),
        patch(
            'app.mobile.routes.servers.get_hidden_host_uuids',
            AsyncMock(return_value=hidden_uuids or set()),
        ),
    ):
        return await list_mobile_servers(db=object())


async def test_list_mobile_servers_returns_visible_servers():
    visible = _make_host(uuid='vis-1', name='Visible', is_disabled=False, is_hidden=False)
    hidden = _make_host(uuid='hid-1', name='Hidden', is_hidden=True)
    disabled = _make_host(uuid='dis-1', name='Disabled', is_disabled=True)

    result = await _call([visible, hidden, disabled])

    assert isinstance(result, MobileServerListResponse)
    assert result.total == 1
    assert len(result.servers) == 1
    assert result.servers[0].uuid == 'vis-1'


async def test_list_mobile_servers_link_is_always_null():
    result = await _call([_make_host()])
    assert result.servers[0].link is None


async def test_list_mobile_servers_is_disabled_always_true():
    result = await _call([_make_host(is_disabled=False)])
    assert result.servers[0].isDisabled is True


async def test_list_mobile_servers_is_connected_always_false():
    result = await _call([_make_host(is_connected=True)])
    assert result.servers[0].isConnected is False


async def test_list_mobile_servers_maps_fields_correctly():
    host = _make_host(
        uuid='u-1',
        name='My Server',
        address='10.0.0.1',
        country_code='FR',
        users_online=42,
        protocol='trojan',
        description='Fast server',
    )

    result = await _call([host])

    server = result.servers[0]
    assert server.uuid == 'u-1'
    assert server.name == 'My Server'
    assert server.address == '10.0.0.1'
    assert server.countryCode == 'FR'
    assert server.usersOnline == 42
    assert server.protocol == 'trojan'
    assert server.description == 'Fast server'


async def test_list_mobile_servers_empty_when_all_filtered():
    hosts = [
        _make_host(uuid='h1', is_hidden=True),
        _make_host(uuid='h2', is_disabled=True),
        _make_host(uuid='h3', is_hidden=True, is_disabled=True),
    ]

    result = await _call(hosts)

    assert result.total == 0
    assert result.servers == []


async def test_list_mobile_servers_excludes_admin_hidden_hosts():
    """Hosts explicitly hidden from the public catalog by an admin (e.g. the
    reserve-grace squad's hosts) must not appear, even though they're not
    hidden/disabled in the panel itself — real subscribers still see them."""
    regular = _make_host(uuid='vis-1', name='Regular Server')
    reserve = _make_host(uuid='reserve-1', name='Бесплатный доступ Telegram')

    result = await _call([regular, reserve], hidden_uuids={'reserve-1'})

    assert result.total == 1
    assert result.servers[0].uuid == 'vis-1'


async def test_list_mobile_servers_returns_503_when_not_configured():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await _call([], is_configured=False)

    assert exc_info.value.status_code == 503


async def test_list_mobile_servers_returns_502_on_api_error():
    from fastapi import HTTPException

    mock_api = AsyncMock()
    mock_api.get_hosts = AsyncMock(side_effect=RuntimeError('connection refused'))

    @asynccontextmanager
    async def _get_api_client():
        yield mock_api

    service = MagicMock()
    service.is_configured = True
    service.configuration_error = None
    service.get_api_client = _get_api_client

    with (
        patch('app.mobile.routes.servers.RemnaWaveService', return_value=service),
        patch('app.mobile.routes.servers.get_hidden_host_uuids', AsyncMock(return_value=set())),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await list_mobile_servers(db=object())

    assert exc_info.value.status_code == 502


def test_parse_host_from_api_response():
    """Tests that _parse_host correctly maps Remnawave API JSON to RemnaWaveHost."""
    from app.external.remnawave_api import RemnaWaveAPI

    api = RemnaWaveAPI.__new__(RemnaWaveAPI)

    host_data = {
        'uuid': 'test-uuid',
        'remark': 'Berlin Server',
        'address': '5.6.7.8',
        'countryCode': 'DE',
        'isConnected': True,
        'isDisabled': False,
        'isHidden': False,
        'usersOnline': 10,
        'protocol': 'vless',
        'description': 'High-speed',
    }

    host = api._parse_host(host_data)

    assert host.uuid == 'test-uuid'
    assert host.name == 'Berlin Server'
    assert host.address == '5.6.7.8'
    assert host.country_code == 'DE'
    assert host.is_connected is True
    assert host.is_disabled is False
    assert host.is_hidden is False
    assert host.users_online == 10
    assert host.protocol == 'vless'
    assert host.description == 'High-speed'


def test_parse_host_uses_defaults_for_missing_fields():
    from app.external.remnawave_api import RemnaWaveAPI

    api = RemnaWaveAPI.__new__(RemnaWaveAPI)

    host_data = {
        'uuid': 'min-uuid',
        'remark': 'Minimal',
        'address': '1.1.1.1',
    }

    host = api._parse_host(host_data)

    assert host.country_code == ''
    assert host.is_connected is False
    assert host.is_disabled is False
    assert host.is_hidden is False
    assert host.users_online == 0
    assert host.protocol == 'vless'
    assert host.description is None
