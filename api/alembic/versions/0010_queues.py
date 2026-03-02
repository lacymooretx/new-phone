"""Call queues (ACD) tables and agent_status on extensions

Revision ID: 0010
Revises: 0009
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Queues ──
    op.create_table(
        "queues",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("queue_number", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strategy", sa.String(50), nullable=False, server_default="longest-idle-agent"),
        sa.Column("moh_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("max_wait_time", sa.Integer(), nullable=False, server_default=sa.text("300")),
        sa.Column("max_wait_time_with_no_agent", sa.Integer(), nullable=False, server_default=sa.text("120")),
        sa.Column("tier_rules_apply", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tier_rule_wait_second", sa.Integer(), nullable=False, server_default=sa.text("300")),
        sa.Column("tier_rule_wait_multiply_level", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tier_rule_no_agent_no_wait", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("discard_abandoned_after", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("abandoned_resume_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("caller_exit_key", sa.String(5), nullable=True),
        sa.Column("wrapup_time", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ring_timeout", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("announce_frequency", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("announce_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("overflow_destination_type", sa.String(20), nullable=True),
        sa.Column("overflow_destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("record_calls", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_queues_tenant", "queues", ["tenant_id"])
    op.create_index("ix_queues_tenant_name", "queues", ["tenant_id", "name"], unique=True)
    op.create_index("ix_queues_tenant_number", "queues", ["tenant_id", "queue_number"], unique=True)

    # ── Queue Members ──
    op.create_table(
        "queue_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("queue_id", UUID(as_uuid=True), sa.ForeignKey("queues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_id", UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_queue_members_queue_ext", "queue_members", ["queue_id", "extension_id"], unique=True)
    op.create_index("ix_queue_members_queue_level_pos", "queue_members", ["queue_id", "level", "position"])

    # ── Agent status on extensions ──
    op.add_column("extensions", sa.Column("agent_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("extensions", "agent_status")
    op.drop_table("queue_members")
    op.drop_table("queues")
