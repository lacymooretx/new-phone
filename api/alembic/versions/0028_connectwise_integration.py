"""ConnectWise PSA integration — cw_configs, cw_company_mappings, cw_ticket_logs tables + CDR column

Revision ID: 0028
Revises: 0027
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- cw_configs (per-tenant ConnectWise credentials) ---
    op.create_table(
        "cw_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("company_id", sa.String(100), nullable=False),
        sa.Column("public_key_encrypted", sa.Text, nullable=False),
        sa.Column("private_key_encrypted", sa.Text, nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column(
            "base_url",
            sa.String(500),
            nullable=False,
            server_default="https://na.myconnectwise.net",
        ),
        sa.Column(
            "api_version", sa.String(20), nullable=False, server_default="2025.1"
        ),
        sa.Column("default_board_id", sa.Integer, nullable=True),
        sa.Column("default_status_id", sa.Integer, nullable=True),
        sa.Column("default_type_id", sa.Integer, nullable=True),
        sa.Column(
            "auto_ticket_missed_calls",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_ticket_voicemails",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_ticket_completed_calls",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "min_call_duration_seconds",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- cw_company_mappings ---
    op.create_table(
        "cw_company_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cw_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cw_configs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("cw_company_id", sa.Integer, nullable=False),
        sa.Column("cw_company_name", sa.String(255), nullable=False),
        sa.Column(
            "extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "did_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dids.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "extension_id IS NOT NULL OR did_id IS NOT NULL",
            name="ck_cw_mapping_has_target",
        ),
    )

    # Partial unique indexes for cw_company_mappings
    op.create_index(
        "uq_cw_mapping_config_extension",
        "cw_company_mappings",
        ["cw_config_id", "extension_id"],
        unique=True,
        postgresql_where=sa.text("extension_id IS NOT NULL"),
    )
    op.create_index(
        "uq_cw_mapping_config_did",
        "cw_company_mappings",
        ["cw_config_id", "did_id"],
        unique=True,
        postgresql_where=sa.text("did_id IS NOT NULL"),
    )

    # --- cw_ticket_logs ---
    op.create_table(
        "cw_ticket_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cw_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cw_configs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "cdr_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_detail_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cw_ticket_id", sa.Integer, nullable=False),
        sa.Column("cw_company_id", sa.Integer, nullable=True),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("ticket_summary", sa.Text, nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="created"
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- Add ConnectWise ticket ID to CDR ---
    op.add_column(
        "call_detail_records",
        sa.Column("connectwise_ticket_id", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    # Remove CDR column
    op.drop_column("call_detail_records", "connectwise_ticket_id")

    # Drop tables in reverse dependency order
    op.drop_table("cw_ticket_logs")

    # Drop partial unique indexes before dropping table
    op.drop_index("uq_cw_mapping_config_did", table_name="cw_company_mappings")
    op.drop_index("uq_cw_mapping_config_extension", table_name="cw_company_mappings")
    op.drop_table("cw_company_mappings")

    op.drop_table("cw_configs")
