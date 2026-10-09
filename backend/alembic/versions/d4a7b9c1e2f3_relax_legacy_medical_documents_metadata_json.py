"""relax legacy metadata_json constraint on medical_documents

Revision ID: d4a7b9c1e2f3
Revises: c3f9a1d2e4b7
Create Date: 2026-04-03 00:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4a7b9c1e2f3"
down_revision: Union[str, None] = "c3f9a1d2e4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE medical_documents
        SET metadata_json = COALESCE(metadata, '{}'::jsonb)
        WHERE metadata_json IS NULL
        """
    )

    op.execute(
        """
        ALTER TABLE medical_documents
        ALTER COLUMN metadata_json DROP NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE medical_documents
        SET metadata_json = COALESCE(metadata_json, '{}'::jsonb)
        WHERE metadata_json IS NULL
        """
    )

    op.execute(
        """
        ALTER TABLE medical_documents
        ALTER COLUMN metadata_json SET NOT NULL
        """
    )
