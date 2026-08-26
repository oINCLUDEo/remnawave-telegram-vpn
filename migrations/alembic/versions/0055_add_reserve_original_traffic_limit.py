"""add reserve_original_traffic_limit_gb to subscriptions

Revision ID: 0055
Revises: 0054
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0055'
down_revision: Union[str, None] = '0054'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('reserve_original_traffic_limit_gb', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'reserve_original_traffic_limit_gb')
