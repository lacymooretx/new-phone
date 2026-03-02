"""Enable RLS on parking_lots table

Revision ID: 0034
Revises: 0033
Create Date: 2026-02-28
"""

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE parking_lots ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_parking_lots ON parking_lots
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON parking_lots TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON parking_lots FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_parking_lots ON parking_lots")
    op.execute("ALTER TABLE parking_lots DISABLE ROW LEVEL SECURITY")
