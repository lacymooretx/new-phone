"""Phase 54: phone_app_configs table for desk phone XML app settings

Revision ID: 0054
Revises: 0053
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_app_configs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "directory_enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "voicemail_enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "call_history_enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "parking_enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "queue_dashboard_enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "settings_enabled",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "page_size",
            sa.Integer,
            server_default=sa.text("15"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("phone_app_configs")
