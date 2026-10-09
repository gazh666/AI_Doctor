"""add lung sound fields to diagnoses

Revision ID: b2c4d6e8f0a1
Revises: f6a1c2d3e4b5
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c4d6e8f0a1'
down_revision: Union[str, None] = 'f6a1c2d3e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnoses', sa.Column('lung_sound_path', sa.String(), nullable=True))
    op.add_column('diagnoses', sa.Column('lung_sound_result_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'lung_sound_result_json')
    op.drop_column('diagnoses', 'lung_sound_path')