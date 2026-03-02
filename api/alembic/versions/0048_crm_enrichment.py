"""CRM enrichment — crm_configs table + CDR enrichment columns

Revision ID: 0048
Revises: 0047
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── crm_configs (one per tenant) ──
    op.create_table(
        "crm_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("provider_type", sa.String(30), nullable=False),
        sa.Column("encrypted_credentials", sa.Text, nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("cache_ttl_seconds", sa.Integer, nullable=False, server_default="3600"),
        sa.Column("lookup_timeout_seconds", sa.Integer, nullable=False, server_default="5"),
        sa.Column("enrichment_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enrich_inbound", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enrich_outbound", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("custom_fields_map", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_crm_configs_tenant_id", "crm_configs", ["tenant_id"])

    # ── CDR enrichment columns ──
    op.add_column(
        "call_detail_records",
        sa.Column("crm_customer_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_company_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_account_number", sa.String(100), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_account_status", sa.String(50), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_contact_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_provider_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_deep_link_url", sa.String(1000), nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_custom_fields", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "call_detail_records",
        sa.Column("crm_matched_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial indexes on CRM columns (WHERE NOT NULL) for fast lookups
    op.create_index(
        "ix_cdr_crm_customer_name",
        "call_detail_records",
        ["crm_customer_name"],
        postgresql_where=sa.text("crm_customer_name IS NOT NULL"),
    )
    op.create_index(
        "ix_cdr_crm_company_name",
        "call_detail_records",
        ["crm_company_name"],
        postgresql_where=sa.text("crm_company_name IS NOT NULL"),
    )
    op.create_index(
        "ix_cdr_crm_account_number",
        "call_detail_records",
        ["crm_account_number"],
        postgresql_where=sa.text("crm_account_number IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_cdr_crm_account_number", table_name="call_detail_records")
    op.drop_index("ix_cdr_crm_company_name", table_name="call_detail_records")
    op.drop_index("ix_cdr_crm_customer_name", table_name="call_detail_records")

    op.drop_column("call_detail_records", "crm_matched_at")
    op.drop_column("call_detail_records", "crm_custom_fields")
    op.drop_column("call_detail_records", "crm_deep_link_url")
    op.drop_column("call_detail_records", "crm_provider_type")
    op.drop_column("call_detail_records", "crm_contact_id")
    op.drop_column("call_detail_records", "crm_account_status")
    op.drop_column("call_detail_records", "crm_account_number")
    op.drop_column("call_detail_records", "crm_company_name")
    op.drop_column("call_detail_records", "crm_customer_name")

    op.drop_table("crm_configs")
