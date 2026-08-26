"""add reserve squad grace period fields to subscriptions

Revision ID: 0054
Revises: 0053
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0054'
down_revision: Union[str, None] = '0053'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('reserve_access_granted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'subscriptions',
        sa.Column('reserve_original_squads', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'reserve_original_squads')
    op.drop_column('subscriptions', 'reserve_access_granted_at')
