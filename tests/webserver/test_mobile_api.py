"""Тесты публичного мобильного API — схемы и логика преобразования данных."""

from __future__ import annotations

from app.webapi.schemas.mobile_api import MobileServerListResponse, MobileServerResponse


def _make_response(**kwargs) -> MobileServerResponse:
    """Вспомогательная функция для создания ответа с разумными дефолтами."""
    defaults = {
        'uuid': 'test-uuid',
        'name': 'Test Server',
        'is_connected': True,
        'is_disabled': True,
        'users_online': 0,
    }
    defaults.update(kwargs)
    return MobileServerResponse(**defaults)


# ── Тесты схемы MobileServerResponse ─────────────────────────────────────────


def test_mobile_server_response_camelcase_aliases() -> None:
    """Сериализация использует camelCase (Flutter-совместимые имена полей)."""
    resp = _make_response(
        country_code='DE',
        users_online=42,
    )
    data = resp.model_dump(by_alias=True)
    assert 'countryCode' in data
    assert 'isConnected' in data
    assert 'isDisabled' in data
    assert 'usersOnline' in data
    assert data['countryCode'] == 'DE'
    assert data['usersOnline'] == 42


def test_mobile_server_response_link_always_none() -> None:
    """Поле link всегда None — сервера видны, но не подключаемы."""
    resp = _make_response()
    assert resp.link is None
    data = resp.model_dump(by_alias=True)
    assert data['link'] is None


def test_mobile_server_response_is_disabled_true() -> None:
    """isDisabled обязан быть True для публичного каталога."""
    resp = _make_response(is_disabled=True)
    assert resp.is_disabled is True


def test_mobile_server_response_optional_fields_nullable() -> None:
    """address, countryCode, protocol, description могут быть None."""
    resp = _make_response(
        address=None,
        country_code=None,
        protocol=None,
        description=None,
    )
    assert resp.address is None
    assert resp.country_code is None
    assert resp.protocol is None
    assert resp.description is None


def test_mobile_server_response_is_connected_reflects_availability() -> None:
    """isConnected отражает доступность сервера."""
    online = _make_response(is_connected=True)
    offline = _make_response(is_connected=False)
    assert online.is_connected is True
    assert offline.is_connected is False


def test_mobile_server_list_response_structure() -> None:
    """MobileServerListResponse содержит ключ 'servers' со списком."""
    items = [
        _make_response(uuid='a', name='Server A'),
        _make_response(uuid='b', name='Server B'),
    ]
    resp = MobileServerListResponse(servers=items)
    data = resp.model_dump(by_alias=True)
    assert 'servers' in data
    assert len(data['servers']) == 2


def test_mobile_server_list_response_empty() -> None:
    """Пустой список серверов корректно сериализуется."""
    resp = MobileServerListResponse(servers=[])
    assert resp.model_dump(by_alias=True) == {'servers': []}


def test_mobile_server_response_from_json_roundtrip() -> None:
    """Десериализация camelCase JSON совместима с Flutter ServerNode.fromJson."""
    json_payload = {
        'uuid': 'server-uuid-1',
        'name': '🇩🇪 Germany',
        'address': None,
        'countryCode': 'DE',
        'isConnected': True,
        'isDisabled': True,
        'usersOnline': 15,
        'link': None,
        'protocol': None,
        'description': 'Test',
    }
    # Pydantic can deserialise both alias and snake_case names.
    resp = MobileServerResponse.model_validate(json_payload)
    assert resp.uuid == 'server-uuid-1'
    assert resp.name == '🇩🇪 Germany'
    assert resp.country_code == 'DE'
    assert resp.is_connected is True
    assert resp.is_disabled is True
    assert resp.users_online == 15
    assert resp.link is None
