"""Phase 9: caller_id_rules, holiday_calendars, holiday_entries tables + column additions

Revision ID: 0016
Revises: 0015
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ALTER existing tables ──

    # tenants: default MOH prompt
    op.add_column(
        "tenants",
        sa.Column(
            "default_moh_prompt_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ring_groups: MOH prompt
    op.add_column(
        "ring_groups",
        sa.Column(
            "moh_prompt_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── New tables ──

    # holiday_calendars (must come before time_conditions FK)
    op.create_table(
        "holiday_calendars",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # holiday_entries (child of holiday_calendars)
    op.create_table(
        "holiday_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("calendar_id", UUID(as_uuid=True), sa.ForeignKey("holiday_calendars.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("recur_annually", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("all_day", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("start_time", sa.Time, nullable=True),
        sa.Column("end_time", sa.Time, nullable=True),
    )
    op.create_index("ix_holiday_entries_calendar_date", "holiday_entries", ["calendar_id", "date"])

    # time_conditions: holiday calendar FK + manual override
    op.add_column(
        "time_conditions",
        sa.Column(
            "holiday_calendar_id",
            UUID(as_uuid=True),
            sa.ForeignKey("holiday_calendars.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "time_conditions",
        sa.Column("manual_override", sa.String(10), nullable=True),
    )

    # caller_id_rules
    op.create_table(
        "caller_id_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rule_type", sa.String(10), nullable=False),
        sa.Column("match_pattern", sa.String(40), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_caller_id_rules_tenant_priority", "caller_id_rules", ["tenant_id", sa.text("priority DESC")])


def downgrade() -> None:
    op.drop_table("caller_id_rules")
    op.drop_column("time_conditions", "manual_override")
    op.drop_column("time_conditions", "holiday_calendar_id")
    op.drop_table("holiday_entries")
    op.drop_table("holiday_calendars")
    op.drop_column("ring_groups", "moh_prompt_id")
    op.drop_column("tenants", "default_moh_prompt_id")
