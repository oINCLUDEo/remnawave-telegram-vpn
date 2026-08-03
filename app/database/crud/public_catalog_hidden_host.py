"""CRUD for admin-managed exclusions from the guest server-catalog preview.

See PublicCatalogHiddenHost's docstring (app/database/models.py) for why this
operates on raw panel host UUIDs rather than ServerSquad.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PublicCatalogHiddenHost


async def get_hidden_host_uuids(db: AsyncSession) -> set[str]:
    result = await db.execute(select(PublicCatalogHiddenHost.host_uuid))
    return set(result.scalars().all())


async def list_hidden_hosts(db: AsyncSession) -> list[PublicCatalogHiddenHost]:
    result = await db.execute(select(PublicCatalogHiddenHost).order_by(PublicCatalogHiddenHost.host_name))
    return list(result.scalars().all())


async def hide_host(db: AsyncSession, host_uuid: str, host_name: str | None) -> None:
    """Idempotent — re-hiding an already-hidden host just refreshes the name snapshot."""
    stmt = (
        pg_insert(PublicCatalogHiddenHost)
        .values(host_uuid=host_uuid, host_name=host_name)
        .on_conflict_do_update(index_elements=[PublicCatalogHiddenHost.host_uuid], set_={'host_name': host_name})
    )
    await db.execute(stmt)
    await db.commit()


async def unhide_host(db: AsyncSession, host_uuid: str) -> None:
    await db.execute(delete(PublicCatalogHiddenHost).where(PublicCatalogHiddenHost.host_uuid == host_uuid))
    await db.commit()
