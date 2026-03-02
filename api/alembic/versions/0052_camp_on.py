"""Camp-On / Automatic Callback — camp_on_configs + camp_on_requests tables

Revision ID: 0052
Revises: 0051
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── camp_on_configs (one per tenant) ──
    op.create_table(
        "camp_on_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("feature_code", sa.String(20), nullable=False, server_default="*88"),
        sa.Column("timeout_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("max_camp_ons_per_target", sa.Integer, nullable=False, server_default="5"),
        sa.Column("callback_retry_delay_seconds", sa.Integer, nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_camp_on_configs_tenant_id", "camp_on_configs", ["tenant_id"])

    # ── camp_on_requests ──
    op.create_table(
        "camp_on_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "caller_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("caller_extension_number", sa.String(20), nullable=False),
        sa.Column("target_extension_number", sa.String(20), nullable=False),
        sa.Column("caller_sip_username", sa.String(100), nullable=False),
        sa.Column("target_sip_username", sa.String(100), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("callback_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("callback_initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_call_id", sa.String(255), nullable=True),
        sa.Column("callback_call_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_camp_on_requests_tenant_id", "camp_on_requests", ["tenant_id"])
    op.create_index(
        "ix_camp_on_requests_target_status",
        "camp_on_requests",
        ["target_extension_id", "status"],
    )
    op.create_index(
        "ix_camp_on_requests_expires",
        "camp_on_requests",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_camp_on_requests_expires", table_name="camp_on_requests")
    op.drop_index("ix_camp_on_requests_target_status", table_name="camp_on_requests")
    op.drop_index("ix_camp_on_requests_tenant_id", table_name="camp_on_requests")
    op.drop_table("camp_on_requests")

    op.drop_index("ix_camp_on_configs_tenant_id", table_name="camp_on_configs")
    op.drop_table("camp_on_configs")
