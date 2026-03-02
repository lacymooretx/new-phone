"""Add lifecycle state and quotas to tenants, provider fields to sip_trunks

Revision ID: 0057
Revises: 0056
Create Date: 2026-03-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- tenants table: lifecycle state and quotas ---
    op.add_column(
        "tenants",
        sa.Column("lifecycle_state", sa.String(20), nullable=False, server_default="trial"),
    )
    op.add_column(
        "tenants",
        sa.Column("max_extensions", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("max_dids", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("max_concurrent_calls", sa.Integer(), nullable=True),
    )

    # --- sip_trunks table: provider fields ---
    op.add_column(
        "sip_trunks",
        sa.Column("provider_type", sa.String(20), nullable=True),
    )
    op.add_column(
        "sip_trunks",
        sa.Column("provider_trunk_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sip_trunks", "provider_trunk_id")
    op.drop_column("sip_trunks", "provider_type")
    op.drop_column("tenants", "max_concurrent_calls")
    op.drop_column("tenants", "max_dids")
    op.drop_column("tenants", "max_extensions")
    op.drop_column("tenants", "lifecycle_state")
