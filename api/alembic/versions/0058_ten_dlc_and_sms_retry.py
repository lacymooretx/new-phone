"""10DLC compliance tables and SMS retry columns

Revision ID: 0058
Revises: 0056
Create Date: 2026-03-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0058"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ten_dlc_brands ─────────────────────────────────────────────
    op.create_table(
        "ten_dlc_brands",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ein", sa.String(20), nullable=False),
        sa.Column("ein_issuing_country", sa.String(2), nullable=False, server_default="US"),
        sa.Column("brand_type", sa.String(20), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("provider_brand_id", sa.String(255), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── ten_dlc_campaigns ──────────────────────────────────────────
    op.create_table(
        "ten_dlc_campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("brand_id", UUID(as_uuid=True), sa.ForeignKey("ten_dlc_brands.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("use_case", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("sample_messages", JSONB, nullable=True),
        sa.Column("message_flow", sa.Text, nullable=False),
        sa.Column("help_message", sa.String(500), nullable=False),
        sa.Column("opt_out_message", sa.String(500), nullable=False),
        sa.Column("opt_in_keywords", sa.String(255), nullable=False, server_default="START"),
        sa.Column("opt_out_keywords", sa.String(255), nullable=False, server_default="STOP"),
        sa.Column("help_keywords", sa.String(255), nullable=False, server_default="HELP"),
        sa.Column("number_pool", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("provider_campaign_id", sa.String(255), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── ten_dlc_compliance_docs ────────────────────────────────────
    op.create_table(
        "ten_dlc_compliance_docs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("brand_id", UUID(as_uuid=True), sa.ForeignKey("ten_dlc_brands.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── SMS retry columns on messages table ────────────────────────
    op.add_column("messages", sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("messages", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"))

    # Index for the retry query
    op.create_index(
        "ix_messages_retry_lookup",
        "messages",
        ["status", "retry_count", "next_retry_at"],
        postgresql_where=sa.text("status = 'failed'"),
    )

    # ── RLS policies for all 3 new tables ──────────────────────────
    for table in ("ten_dlc_brands", "ten_dlc_campaigns", "ten_dlc_compliance_docs"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")


def downgrade() -> None:
    # Drop RLS policies and grants
    for table in ("ten_dlc_compliance_docs", "ten_dlc_campaigns", "ten_dlc_brands"):
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop retry columns
    op.drop_index("ix_messages_retry_lookup", table_name="messages")
    op.drop_column("messages", "max_retries")
    op.drop_column("messages", "next_retry_at")
    op.drop_column("messages", "retry_count")

    # Drop tables in reverse dependency order
    op.drop_table("ten_dlc_compliance_docs")
    op.drop_table("ten_dlc_campaigns")
    op.drop_table("ten_dlc_brands")
