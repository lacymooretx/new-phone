"""Recording storage tiering — recording_tier_configs table + Recording tiering columns

Revision ID: 0050
Revises: 0049
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── recording_tier_configs (one per tenant) ──
    op.create_table(
        "recording_tier_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("hot_tier_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("cold_tier_retention_days", sa.Integer, nullable=False, server_default="365"),
        sa.Column("retrieval_cache_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("auto_tier_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("auto_delete_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_recording_tier_configs_tenant_id", "recording_tier_configs", ["tenant_id"])

    # ── Recording tiering columns ──
    op.add_column(
        "recordings", sa.Column("storage_tier", sa.String(10), nullable=False, server_default="hot")
    )
    op.add_column("recordings", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recordings", sa.Column("archive_storage_path", sa.String(500), nullable=True))
    op.add_column("recordings", sa.Column("archive_storage_bucket", sa.String(100), nullable=True))
    op.add_column(
        "recordings", sa.Column("retrieval_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "recordings", sa.Column("retrieval_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "recordings", sa.Column("legal_hold", sa.Boolean, nullable=False, server_default="false")
    )
    op.add_column(
        "recordings",
        sa.Column(
            "legal_hold_set_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "recordings", sa.Column("legal_hold_set_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "recordings", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True)
    )

    # Composite index for tier queries
    op.create_index("ix_recordings_storage_tier", "recordings", ["tenant_id", "storage_tier"])

    # Partial index for retention cleanup job
    op.create_index(
        "ix_recordings_retention_expires",
        "recordings",
        ["retention_expires_at"],
        postgresql_where=sa.text("retention_expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_recordings_retention_expires", table_name="recordings")
    op.drop_index("ix_recordings_storage_tier", table_name="recordings")

    op.drop_column("recordings", "retention_expires_at")
    op.drop_column("recordings", "legal_hold_set_at")
    op.drop_column("recordings", "legal_hold_set_by")
    op.drop_column("recordings", "legal_hold")
    op.drop_column("recordings", "retrieval_expires_at")
    op.drop_column("recordings", "retrieval_requested_at")
    op.drop_column("recordings", "archive_storage_bucket")
    op.drop_column("recordings", "archive_storage_path")
    op.drop_column("recordings", "archived_at")
    op.drop_column("recordings", "storage_tier")

    op.drop_table("recording_tier_configs")
