"""Enable RLS on phone_app_configs table

Revision ID: 0055
Revises: 0054
Create Date: 2026-03-01
"""

from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE phone_app_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_phone_app_configs ON phone_app_configs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON phone_app_configs TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON phone_app_configs FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_phone_app_configs ON phone_app_configs")
    op.execute("ALTER TABLE phone_app_configs DISABLE ROW LEVEL SECURITY")
