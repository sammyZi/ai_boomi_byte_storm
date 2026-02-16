"""add_protein_pdbqt_data_column

Revision ID: a5f74b45a392
Revises: 075d4cc0643c
Create Date: 2026-02-14 12:19:55.788004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5f74b45a392'
down_revision: Union[str, None] = '075d4cc0643c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add protein_pdbqt_data column to store protein structure for visualization
    op.add_column('docking_jobs', sa.Column('protein_pdbqt_data', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove protein_pdbqt_data column
    op.drop_column('docking_jobs', 'protein_pdbqt_data')
