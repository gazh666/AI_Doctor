"""add trusted medical evidence source catalog

Revision ID: f6a1c2d3e4b5
Revises: d4a7b9c1e2f3
Create Date: 2026-04-26 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "f6a1c2d3e4b5"
down_revision: Union[str, None] = "d4a7b9c1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    indexes = inspector.get_indexes(table_name)
    return any(idx.get("name") == index_name for idx in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "medical_evidence_sources"):
        op.create_table(
            "medical_evidence_sources",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("excerpt", sa.Text(), nullable=False),
            sa.Column("condition_tags", sa.JSON(), nullable=True),
            sa.Column("evidence_level", sa.String(), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("embedding", Vector(768), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "medical_evidence_sources", op.f("ix_medical_evidence_sources_id")):
        op.create_index(op.f("ix_medical_evidence_sources_id"), "medical_evidence_sources", ["id"], unique=False)
    if not _index_exists(inspector, "medical_evidence_sources", op.f("ix_medical_evidence_sources_provider")):
        op.create_index(op.f("ix_medical_evidence_sources_provider"), "medical_evidence_sources", ["provider"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(inspector, "medical_evidence_sources", op.f("ix_medical_evidence_sources_provider")):
        op.drop_index(op.f("ix_medical_evidence_sources_provider"), table_name="medical_evidence_sources")
    if _index_exists(inspector, "medical_evidence_sources", op.f("ix_medical_evidence_sources_id")):
        op.drop_index(op.f("ix_medical_evidence_sources_id"), table_name="medical_evidence_sources")
    if _table_exists(inspector, "medical_evidence_sources"):
        op.drop_table("medical_evidence_sources")
