"""Create boss_admin_relationships table and CDR on-behalf-of columns

Revision ID: 0037
Revises: 0036
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── boss_admin_relationships ──
    op.create_table(
        "boss_admin_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "executive_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assistant_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "filter_mode",
            sa.String(30),
            nullable=False,
            server_default="all_to_assistant",
        ),
        sa.Column(
            "overflow_ring_time",
            sa.Integer,
            nullable=False,
            server_default="20",
        ),
        sa.Column(
            "dnd_override_enabled",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "vip_caller_ids",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default="true",
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
        sa.UniqueConstraint(
            "executive_extension_id",
            "assistant_extension_id",
            name="uq_boss_admin_exec_asst",
        ),
    )
    op.create_index(
        "ix_boss_admin_executive",
        "boss_admin_relationships",
        ["executive_extension_id"],
    )
    op.create_index(
        "ix_boss_admin_assistant",
        "boss_admin_relationships",
        ["assistant_extension_id"],
    )

    # ── CDR on-behalf-of tracking columns ──
    op.add_column(
        "call_detail_records",
        sa.Column(
            "answered_by_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "call_detail_records",
        sa.Column(
            "on_behalf_of_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("call_detail_records", "on_behalf_of_extension_id")
    op.drop_column("call_detail_records", "answered_by_extension_id")
    op.drop_table("boss_admin_relationships")
