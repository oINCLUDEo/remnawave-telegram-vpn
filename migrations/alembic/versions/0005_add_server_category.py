"""add category column to server_squads

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-25

Adds a ``category`` text field to server_squads so the admin can group
servers into named categories (e.g. "whitelist", "youtube", "premium")
that are surfaced to the Flutter mobile app.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not _has_column('server_squads', 'category'):
        op.add_column(
            'server_squads',
            sa.Column(
                'category',
                sa.String(50),
                nullable=False,
                server_default='general',
            ),
        )


def downgrade() -> None:
    op.drop_column('server_squads', 'category')
