"""Regression tests for sync_with_remnawave with no pre-existing promo groups.

Reproduces the bug reported in production:
    ValueError: Server squad must be linked to at least one promo group

The error occurred on fresh installs where no default PromoGroup existed when
sync_with_remnawave (called during startup or via /api/servers/sync) tried to
create new ServerSquad records.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_promo_group(group_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=group_id,
        name='Базовый юзер',
        is_default=True,
        server_discount_percent=0,
        traffic_discount_percent=0,
        device_discount_percent=0,
    )


# ---------------------------------------------------------------------------
# Tests for _get_or_create_default_promo_group
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_or_create_default_promo_group_returns_existing() -> None:
    """When a default promo group already exists it is returned without INSERT."""
    from app.database.crud.server_squad import _get_or_create_default_promo_group

    existing = _fake_promo_group(7)

    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    db.execute.return_value = result

    group = await _get_or_create_default_promo_group(db)

    assert group is existing
    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_get_or_create_default_promo_group_creates_when_missing() -> None:
    """When no default promo group exists a new one is added and flushed."""
    from app.database.crud.server_squad import _get_or_create_default_promo_group
    from app.database.models import PromoGroup

    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalars.return_value.first.return_value = None
    db.execute.return_value = empty_result
    db.add = MagicMock()
    db.flush = AsyncMock()

    group = await _get_or_create_default_promo_group(db)

    assert isinstance(group, PromoGroup)
    assert group.is_default is True
    assert group.name == 'Базовый юзер'
    db.add.assert_called_once_with(group)
    db.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests for sync_with_remnawave via patching
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sync_with_remnawave_no_promo_groups_does_not_raise() -> None:
    """sync_with_remnawave must not raise ValueError when no PromoGroup exists.

    Regression for: ValueError: Server squad must be linked to at least one
    promo group  — triggered on fresh installs.
    """
    from app.database.crud.server_squad import sync_with_remnawave

    db = AsyncMock()

    # No existing servers in DB
    empty_servers_result = MagicMock()
    empty_servers_result.scalars.return_value.all.return_value = []
    db.execute.return_value = empty_servers_result

    fake_group = _fake_promo_group(1)

    # Patch both internal helpers to keep the test pure
    with (
        patch(
            'app.database.crud.server_squad._get_or_create_default_promo_group',
            new=AsyncMock(return_value=fake_group),
        ),
        patch(
            'app.database.crud.server_squad.create_server_squad',
            new=AsyncMock(),
        ) as mock_create,
    ):
        squads = [{'uuid': 'test-uuid-1', 'name': 'RU-Squad-01'}]
        created, updated, removed = await sync_with_remnawave(db, squads)

    assert created == 1
    assert updated == 0
    assert removed == 0
    mock_create.assert_awaited_once()
    # promo_group_ids must be passed explicitly
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get('promo_group_ids') == [fake_group.id]


@pytest.mark.anyio
async def test_sync_with_remnawave_only_updates_no_promo_group_needed() -> None:
    """If all squads already exist in the DB, no promo group look-up is needed."""
    from app.database.crud.server_squad import sync_with_remnawave

    existing_server = MagicMock()
    existing_server.squad_uuid = 'test-uuid-3'
    existing_server.original_name = 'Old Name'

    db = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalars.return_value.all.return_value = [existing_server]
    db.execute.return_value = existing_result

    with patch(
        'app.database.crud.server_squad._get_or_create_default_promo_group',
        new=AsyncMock(),
    ) as mock_promo:
        squads = [{'uuid': 'test-uuid-3', 'name': 'New Name'}]
        created, updated, removed = await sync_with_remnawave(db, squads)

    assert created == 0
    assert updated == 1
    # No promo group interaction when only updates occur
    mock_promo.assert_not_awaited()


@pytest.mark.anyio
async def test_sync_with_remnawave_multiple_new_squads_promo_group_fetched_once() -> None:
    """Default PromoGroup is fetched/created only once even for multiple new squads."""
    from app.database.crud.server_squad import sync_with_remnawave

    db = AsyncMock()

    empty_servers_result = MagicMock()
    empty_servers_result.scalars.return_value.all.return_value = []
    db.execute.return_value = empty_servers_result

    fake_group = _fake_promo_group(1)

    with (
        patch(
            'app.database.crud.server_squad._get_or_create_default_promo_group',
            new=AsyncMock(return_value=fake_group),
        ) as mock_promo,
        patch(
            'app.database.crud.server_squad.create_server_squad',
            new=AsyncMock(),
        ),
    ):
        squads = [
            {'uuid': 'uuid-a', 'name': 'RU-01'},
            {'uuid': 'uuid-b', 'name': 'DE-01'},
        ]
        created, updated, removed = await sync_with_remnawave(db, squads)

    assert created == 2
    # Must be called exactly once regardless of how many new squads
    mock_promo.assert_awaited_once()

