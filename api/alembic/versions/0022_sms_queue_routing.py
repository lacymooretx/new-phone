"""Add sms_queue_id to dids table for SMS queue routing

Revision ID: 0022
Revises: 0021
Create Date: 2026-02-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dids",
        sa.Column(
            "sms_queue_id",
            UUID(as_uuid=True),
            sa.ForeignKey("queues.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_dids_sms_queue_id", "dids", ["sms_queue_id"])


def downgrade() -> None:
    op.drop_index("ix_dids_sms_queue_id", table_name="dids")
    op.drop_column("dids", "sms_queue_id")
