"""add voice interactions table

Revision ID: 0d08a98674b0
Revises: 
Create Date: 2026-02-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0d08a98674b0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # We ONLY want to create the new table. 
    # All op.drop_table commands have been removed for safety.
    op.create_table('voice_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('patient_id', sa.Integer(), nullable=True),
        sa.Column('audio_filename', sa.String(), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voice_interactions_id'), 'voice_interactions', ['id'], unique=False)
    op.create_index(op.f('ix_voice_interactions_session_id'), 'voice_interactions', ['session_id'], unique=False)

def downgrade() -> None:
    # Downgrade should only remove the table we just added
    op.drop_index(op.f('ix_voice_interactions_session_id'), table_name='voice_interactions')
    op.drop_index(op.f('ix_voice_interactions_id'), table_name='voice_interactions')
    op.drop_table('voice_interactions')