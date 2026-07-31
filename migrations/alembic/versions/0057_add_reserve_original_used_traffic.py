"""add reserve_original_used_traffic_bytes to subscriptions

Revision ID: 0057
Revises: 0056
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0057'
down_revision: Union[str, None] = '0056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('reserve_original_used_traffic_bytes', sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'reserve_original_used_traffic_bytes')
