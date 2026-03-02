"""CDR queue_id FK + composite analytics indexes

Revision ID: 0032
Revises: 0031
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add queue_id FK column to call_detail_records
    op.add_column(
        "call_detail_records",
        sa.Column(
            "queue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("queues.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Composite indexes for analytics performance
    op.create_index(
        "ix_cdr_tenant_direction",
        "call_detail_records",
        ["tenant_id", "direction"],
    )
    op.create_index(
        "ix_cdr_tenant_disposition",
        "call_detail_records",
        ["tenant_id", "disposition"],
    )
    op.create_index(
        "ix_cdr_tenant_did",
        "call_detail_records",
        ["tenant_id", "did_id"],
    )
    op.create_index(
        "ix_cdr_tenant_queue",
        "call_detail_records",
        ["tenant_id", "queue_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cdr_tenant_queue", table_name="call_detail_records")
    op.drop_index("ix_cdr_tenant_did", table_name="call_detail_records")
    op.drop_index("ix_cdr_tenant_disposition", table_name="call_detail_records")
    op.drop_index("ix_cdr_tenant_direction", table_name="call_detail_records")
    op.drop_column("call_detail_records", "queue_id")
