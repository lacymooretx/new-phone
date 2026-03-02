"""Create sites table

Revision ID: 0039
Revises: 0038
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="America/New_York"),
        sa.Column("address_street", sa.String(255), nullable=True),
        sa.Column("address_city", sa.String(100), nullable=True),
        sa.Column("address_state", sa.String(50), nullable=True),
        sa.Column("address_zip", sa.String(20), nullable=True),
        sa.Column("address_country", sa.String(2), nullable=False, server_default="US"),
        sa.Column("outbound_cid_name", sa.String(100), nullable=True),
        sa.Column("outbound_cid_number", sa.String(20), nullable=True),
        sa.Column(
            "moh_prompt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_sites_tenant_name"),
    )


def downgrade() -> None:
    op.drop_table("sites")
