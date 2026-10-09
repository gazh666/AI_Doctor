"""add clinical workflow tables

Revision ID: 8b1d2c3a4f5e
Revises: 0e5221ac801d
Create Date: 2026-04-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b1d2c3a4f5e"
down_revision: Union[str, None] = "0e5221ac801d"
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

    if not _table_exists(inspector, "triage_assessments"):
        op.create_table(
            "triage_assessments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("symptoms_text", sa.Text(), nullable=False),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("vitals", sa.JSON(), nullable=True),
            sa.Column("risk_factors", sa.JSON(), nullable=True),
            sa.Column("urgency_level", sa.String(), nullable=False),
            sa.Column("red_flags", sa.JSON(), nullable=True),
            sa.Column("rationale", sa.Text(), nullable=True),
            sa.Column("recommended_action", sa.Text(), nullable=False),
            sa.Column("escalated", sa.Boolean(), nullable=True),
            sa.Column("escalation_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "triage_assessments", op.f("ix_triage_assessments_id")):
        op.create_index(op.f("ix_triage_assessments_id"), "triage_assessments", ["id"], unique=False)

    if not _table_exists(inspector, "followup_plans"):
        op.create_table(
            "followup_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("diagnosis_id", sa.Integer(), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("channel", sa.String(), nullable=True),
            sa.Column("reminder_enabled", sa.Boolean(), nullable=True),
            sa.Column("reminder_sent", sa.Boolean(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("outcome", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnoses.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "followup_plans", op.f("ix_followup_plans_id")):
        op.create_index(op.f("ix_followup_plans_id"), "followup_plans", ["id"], unique=False)

    if not _table_exists(inspector, "medication_safety_checks"):
        op.create_table(
            "medication_safety_checks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=True),
            sa.Column("medications", sa.JSON(), nullable=False),
            sa.Column("allergies", sa.JSON(), nullable=True),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("risk_level", sa.String(), nullable=False),
            sa.Column("interactions", sa.JSON(), nullable=True),
            sa.Column("contraindications", sa.JSON(), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "medication_safety_checks", op.f("ix_medication_safety_checks_id")):
        op.create_index(op.f("ix_medication_safety_checks_id"), "medication_safety_checks", ["id"], unique=False)

    if not _table_exists(inspector, "sync_events"):
        op.create_table(
            "sync_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("device_id", sa.String(), nullable=False),
            sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("entity_id", sa.String(), nullable=False),
            sa.Column("operation", sa.String(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("server_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("sync_status", sa.String(), nullable=True),
            sa.Column("conflict_reason", sa.Text(), nullable=True),
            sa.Column("resolution_strategy", sa.String(), nullable=True),
            sa.Column("resolved_by_user", sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "sync_events", op.f("ix_sync_events_id")):
        op.create_index(op.f("ix_sync_events_id"), "sync_events", ["id"], unique=False)
    if not _index_exists(inspector, "sync_events", op.f("ix_sync_events_device_id")):
        op.create_index(op.f("ix_sync_events_device_id"), "sync_events", ["device_id"], unique=False)

    if not _table_exists(inspector, "ai_decision_audits"):
        op.create_table(
            "ai_decision_audits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("session_id", sa.String(), nullable=True),
            sa.Column("source_endpoint", sa.String(), nullable=False),
            sa.Column("decision_type", sa.String(), nullable=False),
            sa.Column("input_summary", sa.Text(), nullable=True),
            sa.Column("output_summary", sa.Text(), nullable=True),
            sa.Column("confidence_band", sa.String(), nullable=True),
            sa.Column("urgency_level", sa.String(), nullable=True),
            sa.Column("red_flags", sa.JSON(), nullable=True),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("model_version", sa.String(), nullable=True),
            sa.Column("prompt_version", sa.String(), nullable=True),
            sa.Column("override_applied", sa.Boolean(), nullable=True),
            sa.Column("override_reason", sa.Text(), nullable=True),
            sa.Column("clinician_feedback", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(inspector, "ai_decision_audits", op.f("ix_ai_decision_audits_id")):
        op.create_index(op.f("ix_ai_decision_audits_id"), "ai_decision_audits", ["id"], unique=False)
    if not _index_exists(inspector, "ai_decision_audits", op.f("ix_ai_decision_audits_session_id")):
        op.create_index(op.f("ix_ai_decision_audits_session_id"), "ai_decision_audits", ["session_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(inspector, "ai_decision_audits", op.f("ix_ai_decision_audits_session_id")):
        op.drop_index(op.f("ix_ai_decision_audits_session_id"), table_name="ai_decision_audits")
    if _index_exists(inspector, "ai_decision_audits", op.f("ix_ai_decision_audits_id")):
        op.drop_index(op.f("ix_ai_decision_audits_id"), table_name="ai_decision_audits")
    if _table_exists(inspector, "ai_decision_audits"):
        op.drop_table("ai_decision_audits")

    if _index_exists(inspector, "sync_events", op.f("ix_sync_events_device_id")):
        op.drop_index(op.f("ix_sync_events_device_id"), table_name="sync_events")
    if _index_exists(inspector, "sync_events", op.f("ix_sync_events_id")):
        op.drop_index(op.f("ix_sync_events_id"), table_name="sync_events")
    if _table_exists(inspector, "sync_events"):
        op.drop_table("sync_events")

    if _index_exists(inspector, "medication_safety_checks", op.f("ix_medication_safety_checks_id")):
        op.drop_index(op.f("ix_medication_safety_checks_id"), table_name="medication_safety_checks")
    if _table_exists(inspector, "medication_safety_checks"):
        op.drop_table("medication_safety_checks")

    if _index_exists(inspector, "followup_plans", op.f("ix_followup_plans_id")):
        op.drop_index(op.f("ix_followup_plans_id"), table_name="followup_plans")
    if _table_exists(inspector, "followup_plans"):
        op.drop_table("followup_plans")

    if _index_exists(inspector, "triage_assessments", op.f("ix_triage_assessments_id")):
        op.drop_index(op.f("ix_triage_assessments_id"), table_name="triage_assessments")
    if _table_exists(inspector, "triage_assessments"):
        op.drop_table("triage_assessments")
