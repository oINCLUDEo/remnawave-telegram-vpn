"""add public_catalog_hidden_hosts table

Revision ID: 0058
Revises: 0057
Create Date: 2026-08-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0058'
down_revision: Union[str, None] = '0057'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'public_catalog_hidden_hosts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('host_uuid', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('host_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('public_catalog_hidden_hosts')
