"""Add site_id FK to extensions, time_conditions, parking_lots, page_groups, dids, audio_prompts, call_detail_records

Revision ID: 0041
Revises: 0040
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

TABLES = [
    "extensions",
    "time_conditions",
    "parking_lots",
    "page_groups",
    "dids",
    "audio_prompts",
    "call_detail_records",
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "site_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("sites.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{table}_site_id", table, ["site_id"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_site_id", table)
        op.drop_column(table, "site_id")
