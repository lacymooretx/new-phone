"""Audit logs, follow_me, follow_me_destinations tables

Revision ID: 0014
Revises: 0013
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Audit Logs (immutable, no RLS) ──
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_tenant", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])

    # ── Follow Me (tenant-scoped) ──
    op.create_table(
        "follow_me",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_id", UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("strategy", sa.String(30), nullable=False, server_default="sequential"),
        sa.Column("ring_extension_first", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("extension_ring_time", sa.Integer(), nullable=False, server_default=sa.text("25")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_follow_me_tenant", "follow_me", ["tenant_id"])
    op.create_index("ix_follow_me_extension", "follow_me", ["extension_id"], unique=True)

    # ── Follow Me Destinations (child, no tenant_id) ──
    op.create_table(
        "follow_me_destinations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("follow_me_id", UUID(as_uuid=True), sa.ForeignKey("follow_me.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("destination", sa.String(40), nullable=False),
        sa.Column("ring_time", sa.Integer(), nullable=False, server_default=sa.text("20")),
    )
    op.create_index("ix_follow_me_dest_pos", "follow_me_destinations", ["follow_me_id", "position"], unique=True)


def downgrade() -> None:
    op.drop_table("follow_me_destinations")
    op.drop_table("follow_me")
    op.drop_table("audit_logs")
