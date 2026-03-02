"""Create parking_lots table

Revision ID: 0033
Revises: 0032
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parking_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lot_number", sa.Integer, nullable=False),
        sa.Column("slot_start", sa.Integer, nullable=False),
        sa.Column("slot_end", sa.Integer, nullable=False),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="60"),
        sa.Column("comeback_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("comeback_extension", sa.String(50), nullable=True),
        sa.Column(
            "moh_prompt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.UniqueConstraint("tenant_id", "lot_number", name="uq_parking_lots_tenant_lot_number"),
    )


def downgrade() -> None:
    op.drop_table("parking_lots")
