"""add metadata column to medical_documents

Revision ID: c3f9a1d2e4b7
Revises: 8b1d2c3a4f5e
Create Date: 2026-04-03 00:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3f9a1d2e4b7"
down_revision: Union[str, None] = "8b1d2c3a4f5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE medical_documents
        ADD COLUMN IF NOT EXISTS metadata JSONB
        """
    )

    op.execute(
        """
        UPDATE medical_documents
        SET metadata = jsonb_build_object(
            'source',
            COALESCE(NULLIF(title, ''), CONCAT('medical_document_', id::text))
        )
        WHERE metadata IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE medical_documents
        DROP COLUMN IF EXISTS metadata
        """
    )
