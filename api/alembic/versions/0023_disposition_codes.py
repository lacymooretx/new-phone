"""Add disposition code lists/codes tables, alter queues and CDR

Revision ID: 0023
Revises: 0022
Create Date: 2026-02-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── disposition_code_lists ──
    op.create_table(
        "disposition_code_lists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_disposition_code_lists_tenant_id", "disposition_code_lists", ["tenant_id"])

    # ── disposition_codes ──
    op.create_table(
        "disposition_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("disposition_code_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("position", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("list_id", "code", name="uq_disposition_codes_list_code"),
    )
    op.create_index("ix_disposition_codes_tenant_id", "disposition_codes", ["tenant_id"])
    op.create_index("ix_disposition_codes_list_id", "disposition_codes", ["list_id"])

    # ── Alter queues ──
    op.add_column("queues", sa.Column("disposition_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column(
        "queues",
        sa.Column(
            "disposition_code_list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("disposition_code_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_queues_disposition_code_list_id", "queues", ["disposition_code_list_id"])

    # ── Alter call_detail_records ──
    op.add_column(
        "call_detail_records",
        sa.Column(
            "agent_disposition_code_id",
            UUID(as_uuid=True),
            sa.ForeignKey("disposition_codes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("call_detail_records", sa.Column("agent_disposition_notes", sa.Text, nullable=True))
    op.add_column(
        "call_detail_records",
        sa.Column("disposition_entered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_cdr_agent_disposition_code_id",
        "call_detail_records",
        ["agent_disposition_code_id"],
    )


def downgrade() -> None:
    # ── Revert CDR columns ──
    op.drop_index("ix_cdr_agent_disposition_code_id", table_name="call_detail_records")
    op.drop_column("call_detail_records", "disposition_entered_at")
    op.drop_column("call_detail_records", "agent_disposition_notes")
    op.drop_column("call_detail_records", "agent_disposition_code_id")

    # ── Revert queue columns ──
    op.drop_index("ix_queues_disposition_code_list_id", table_name="queues")
    op.drop_column("queues", "disposition_code_list_id")
    op.drop_column("queues", "disposition_required")

    # ── Drop disposition_codes ──
    op.drop_index("ix_disposition_codes_list_id", table_name="disposition_codes")
    op.drop_index("ix_disposition_codes_tenant_id", table_name="disposition_codes")
    op.drop_table("disposition_codes")

    # ── Drop disposition_code_lists ──
    op.drop_index("ix_disposition_code_lists_tenant_id", table_name="disposition_code_lists")
    op.drop_table("disposition_code_lists")
