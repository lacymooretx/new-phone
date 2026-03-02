"""Create workforce management tables

Revision ID: 0044
Revises: 0043
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # wfm_shifts
    op.create_table(
        "wfm_shifts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("break_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_wfm_shifts_tenant_name"),
    )
    op.create_index("ix_wfm_shifts_tenant_id", "wfm_shifts", ["tenant_id"])

    # wfm_schedule_entries
    op.create_table(
        "wfm_schedule_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wfm_shifts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "extension_id", "date", name="uq_wfm_schedule_entries_tenant_ext_date"),
    )
    op.create_index("ix_wfm_schedule_entries_tenant_id", "wfm_schedule_entries", ["tenant_id"])
    op.create_index("ix_wfm_schedule_entries_extension_id", "wfm_schedule_entries", ["extension_id"])
    op.create_index("ix_wfm_schedule_entries_shift_id", "wfm_schedule_entries", ["shift_id"])
    op.create_index("ix_wfm_schedule_entries_date", "wfm_schedule_entries", ["date"])

    # wfm_time_off_requests
    op.create_table(
        "wfm_time_off_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_wfm_time_off_requests_tenant_id", "wfm_time_off_requests", ["tenant_id"])
    op.create_index("ix_wfm_time_off_requests_extension_id", "wfm_time_off_requests", ["extension_id"])

    # wfm_forecast_configs
    op.create_table(
        "wfm_forecast_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("queue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_sla_percent", sa.Integer, nullable=False, server_default="80"),
        sa.Column("target_sla_seconds", sa.Integer, nullable=False, server_default="20"),
        sa.Column("shrinkage_percent", sa.Integer, nullable=False, server_default="30"),
        sa.Column("lookback_weeks", sa.Integer, nullable=False, server_default="8"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "queue_id", name="uq_wfm_forecast_configs_tenant_queue"),
    )
    op.create_index("ix_wfm_forecast_configs_tenant_id", "wfm_forecast_configs", ["tenant_id"])
    op.create_index("ix_wfm_forecast_configs_queue_id", "wfm_forecast_configs", ["queue_id"])


def downgrade() -> None:
    op.drop_table("wfm_forecast_configs")
    op.drop_table("wfm_time_off_requests")
    op.drop_table("wfm_schedule_entries")
    op.drop_table("wfm_shifts")
