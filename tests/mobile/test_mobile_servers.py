"""Tests for the mobile API servers endpoint."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.mobile.routes.servers import list_mobile_servers
from app.mobile.schemas.servers import MobileServerListResponse


def _make_squad(
    squad_uuid: str = 'abc-123',
    display_name: str = 'Test Server',
    country_code: str | None = 'DE',
    current_users: int | None = 5,
    description: str | None = None,
) -> SimpleNamespace:
    """A duck-typed stand-in for the ServerSquad ORM row — only the attributes
    list_mobile_servers actually reads."""
    return SimpleNamespace(
        squad_uuid=squad_uuid,
        display_name=display_name,
        country_code=country_code,
        current_users=current_users,
        description=description,
    )


async def _call(squads: list[SimpleNamespace]) -> MobileServerListResponse:
    with patch(
        'app.mobile.routes.servers.get_available_server_squads',
        AsyncMock(return_value=squads),
    ):
        return await list_mobile_servers(db=object())


async def test_list_mobile_servers_returns_available_squads():
    squad = _make_squad(squad_uuid='vis-1', display_name='Visible')

    result = await _call([squad])

    assert isinstance(result, MobileServerListResponse)
    assert result.total == 1
    assert len(result.servers) == 1
    assert result.servers[0].uuid == 'vis-1'


async def test_list_mobile_servers_link_is_always_null():
    result = await _call([_make_squad()])
    assert result.servers[0].link is None


async def test_list_mobile_servers_is_disabled_always_true():
    result = await _call([_make_squad()])
    assert result.servers[0].isDisabled is True


async def test_list_mobile_servers_is_connected_always_false():
    result = await _call([_make_squad()])
    assert result.servers[0].isConnected is False


async def test_list_mobile_servers_maps_fields_correctly():
    squad = _make_squad(
        squad_uuid='u-1',
        display_name='My Server',
        country_code='FR',
        current_users=42,
        description='Белые списки',
    )

    result = await _call([squad])

    server = result.servers[0]
    assert server.uuid == 'u-1'
    assert server.name == 'My Server'
    assert server.address == 'u-1'
    assert server.countryCode == 'FR'
    assert server.usersOnline == 42
    assert server.description == 'Белые списки'


async def test_list_mobile_servers_defaults_missing_fields():
    squad = _make_squad(country_code=None, current_users=None)

    result = await _call([squad])

    server = result.servers[0]
    assert server.countryCode == ''
    assert server.usersOnline == 0


async def test_list_mobile_servers_empty_when_none_available():
    result = await _call([])

    assert result.total == 0
    assert result.servers == []


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
