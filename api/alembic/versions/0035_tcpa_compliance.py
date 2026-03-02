"""Create TCPA compliance tables

Revision ID: 0035
Revises: 0034
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── dnc_lists ──
    op.create_table(
        "dnc_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("list_type", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── dnc_entries ──
    op.create_table(
        "dnc_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "dnc_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dnc_lists.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column(
            "added_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("dnc_list_id", "phone_number", name="uq_dnc_entries_list_phone"),
    )
    op.create_index("ix_dnc_entries_phone_number", "dnc_entries", ["phone_number"])

    # ── consent_records ──
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("campaign_type", sa.String(20), nullable=False),
        sa.Column("consent_method", sa.String(20), nullable=False),
        sa.Column("consent_text", sa.Text, nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "recorded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_consent_records_phone_number", "consent_records", ["phone_number"])

    # ── compliance_settings ──
    op.create_table(
        "compliance_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("calling_window_start", sa.Time, nullable=False, server_default="08:00:00"),
        sa.Column("calling_window_end", sa.Time, nullable=False, server_default="21:00:00"),
        sa.Column(
            "default_timezone",
            sa.String(50),
            nullable=False,
            server_default="America/New_York",
        ),
        sa.Column("enforce_calling_window", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sync_sms_optout_to_dnc", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("auto_dnc_on_request", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("national_dnc_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", name="uq_compliance_settings_tenant"),
    )

    # ── compliance_audit_logs (immutable — no updated_at) ──
    op.create_table(
        "compliance_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_compliance_audit_logs_tenant_created",
        "compliance_audit_logs",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("compliance_audit_logs")
    op.drop_table("compliance_settings")
    op.drop_table("consent_records")
    op.drop_table("dnc_entries")
    op.drop_table("dnc_lists")
