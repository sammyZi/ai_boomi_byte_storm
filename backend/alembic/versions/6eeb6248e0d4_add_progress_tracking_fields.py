"""add_progress_tracking_fields

Revision ID: 6eeb6248e0d4
Revises: a5f74b45a392
Create Date: 2026-02-14 13:02:48.628783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eeb6248e0d4'
down_revision: Union[str, None] = 'a5f74b45a392'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add progress tracking fields to docking_jobs table
    op.add_column('docking_jobs', sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('docking_jobs', sa.Column('current_step', sa.String(length=100), nullable=True))
    op.add_column('docking_jobs', sa.Column('console_output', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove progress tracking fields from docking_jobs table
    op.drop_column('docking_jobs', 'console_output')
    op.drop_column('docking_jobs', 'current_step')
    op.drop_column('docking_jobs', 'progress_percent')
