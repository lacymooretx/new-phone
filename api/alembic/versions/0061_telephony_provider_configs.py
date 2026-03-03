"""Create telephony_provider_configs table

Revision ID: 0061
Revises: 0060
Create Date: 2026-03-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telephony_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("encrypted_credentials", sa.Text, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
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
    )

    # Partial unique index: one MSP default per provider type
    op.execute("""
        CREATE UNIQUE INDEX uq_telephony_provider_msp_default
        ON telephony_provider_configs (provider_type)
        WHERE tenant_id IS NULL AND is_default AND is_active
    """)

    # Partial unique index: one tenant default per provider type per tenant
    op.execute("""
        CREATE UNIQUE INDEX uq_telephony_provider_tenant_default
        ON telephony_provider_configs (tenant_id, provider_type)
        WHERE tenant_id IS NOT NULL AND is_default AND is_active
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_telephony_provider_tenant_default")
    op.execute("DROP INDEX IF EXISTS uq_telephony_provider_msp_default")
    op.drop_table("telephony_provider_configs")
