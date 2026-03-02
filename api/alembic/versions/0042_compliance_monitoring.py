"""Create compliance monitoring tables and add CDR compliance columns

Revision ID: 0042
Revises: 0041
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # compliance_rules
    op.create_table(
        "compliance_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("rule_text", sa.Text, nullable=False),
        sa.Column("category", sa.String(30), nullable=False, server_default="custom"),
        sa.Column("severity", sa.String(10), nullable=False, server_default="major"),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="all"),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_rules_tenant_id", "compliance_rules", ["tenant_id"])

    # compliance_evaluations
    op.create_table(
        "compliance_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cdr_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("call_detail_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_agent_conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transcript_text", sa.Text, nullable=False),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("rules_passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rules_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rules_not_applicable", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_flagged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider_name", sa.String(50), nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_evaluations_tenant_id", "compliance_evaluations", ["tenant_id"])
    op.create_index("ix_compliance_evaluations_cdr_id", "compliance_evaluations", ["cdr_id"])
    op.create_index("ix_compliance_evaluations_is_flagged", "compliance_evaluations", ["is_flagged"])

    # compliance_rule_results
    op.create_table(
        "compliance_rule_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_evaluations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rule_name_snapshot", sa.String(255), nullable=False),
        sa.Column("rule_text_snapshot", sa.Text, nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("evidence", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_rule_results_tenant_id", "compliance_rule_results", ["tenant_id"])
    op.create_index("ix_compliance_rule_results_evaluation_id", "compliance_rule_results", ["evaluation_id"])

    # Add compliance columns to CDR
    op.add_column(
        "call_detail_records",
        sa.Column("compliance_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column(
            "compliance_evaluation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compliance_evaluations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_call_detail_records_compliance_evaluation_id", "call_detail_records", ["compliance_evaluation_id"])


def downgrade() -> None:
    op.drop_index("ix_call_detail_records_compliance_evaluation_id", "call_detail_records")
    op.drop_column("call_detail_records", "compliance_evaluation_id")
    op.drop_column("call_detail_records", "compliance_score")
    op.drop_table("compliance_rule_results")
    op.drop_table("compliance_evaluations")
    op.drop_table("compliance_rules")
