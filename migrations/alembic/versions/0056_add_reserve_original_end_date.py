"""add reserve_original_end_date to subscriptions

Revision ID: 0056
Revises: 0055
Create Date: 2026-07-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0056'
down_revision: Union[str, None] = '0055'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('reserve_original_end_date', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'reserve_original_end_date')
