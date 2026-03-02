"""Create port_requests and port_request_history tables with RLS

Revision ID: 0059
Revises: 0056
Create Date: 2026-03-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0059"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── port_requests ──────────────────────────────────────────────────
    op.create_table(
        "port_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("numbers", JSONB, nullable=False),
        sa.Column("current_carrier", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="submitted"),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_port_id", sa.String(255), nullable=True),
        sa.Column("loa_file_path", sa.String(500), nullable=True),
        sa.Column("foc_date", sa.Date, nullable=True),
        sa.Column("requested_port_date", sa.Date, nullable=True),
        sa.Column("actual_port_date", sa.Date, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("submitted_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_port_requests_status", "port_requests", ["status"])
    op.create_index("ix_port_requests_provider", "port_requests", ["provider"])

    # ── port_request_history ───────────────────────────────────────────
    op.create_table(
        "port_request_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("port_request_id", UUID(as_uuid=True), sa.ForeignKey("port_requests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── RLS policies ───────────────────────────────────────────────────
    conn = op.get_bind()

    # Enable RLS on port_requests
    conn.execute(sa.text("ALTER TABLE port_requests ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE port_requests FORCE ROW LEVEL SECURITY"))

    conn.execute(sa.text("""
        CREATE POLICY port_requests_tenant_isolation ON port_requests
        USING (tenant_id::text = current_setting('app.current_tenant', true))
    """))

    conn.execute(sa.text("""
        CREATE POLICY port_requests_admin_bypass ON port_requests
        TO new_phone_admin
        USING (true)
        WITH CHECK (true)
    """))

    # Enable RLS on port_request_history (join through port_requests for tenant isolation)
    conn.execute(sa.text("ALTER TABLE port_request_history ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE port_request_history FORCE ROW LEVEL SECURITY"))

    conn.execute(sa.text("""
        CREATE POLICY port_request_history_tenant_isolation ON port_request_history
        USING (
            port_request_id IN (
                SELECT id FROM port_requests
                WHERE tenant_id::text = current_setting('app.current_tenant', true)
            )
        )
    """))

    conn.execute(sa.text("""
        CREATE POLICY port_request_history_admin_bypass ON port_request_history
        TO new_phone_admin
        USING (true)
        WITH CHECK (true)
    """))

    # Grant permissions to app user
    conn.execute(sa.text("GRANT SELECT, INSERT, UPDATE ON port_requests TO new_phone_app"))
    conn.execute(sa.text("GRANT SELECT, INSERT ON port_request_history TO new_phone_app"))


def downgrade() -> None:
    conn = op.get_bind()

    # Drop RLS policies
    conn.execute(sa.text("DROP POLICY IF EXISTS port_request_history_admin_bypass ON port_request_history"))
    conn.execute(sa.text("DROP POLICY IF EXISTS port_request_history_tenant_isolation ON port_request_history"))
    conn.execute(sa.text("DROP POLICY IF EXISTS port_requests_admin_bypass ON port_requests"))
    conn.execute(sa.text("DROP POLICY IF EXISTS port_requests_tenant_isolation ON port_requests"))

    op.drop_table("port_request_history")
    op.drop_table("port_requests")
