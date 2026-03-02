"""Enable RLS on tenant-scoped tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-25
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on users table
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # RLS policy: app user can only see rows matching current tenant
    op.execute("""
        CREATE POLICY tenant_isolation_users ON users
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)

    # Grant table permissions to app user (in case default privileges didn't fire)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON tenants TO new_phone_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON users TO new_phone_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
