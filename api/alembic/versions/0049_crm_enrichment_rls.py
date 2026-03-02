"""Enable RLS on crm_configs table

Revision ID: 0049
Revises: 0048
Create Date: 2026-03-01
"""

from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_crm_configs ON crm_configs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON crm_configs TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON crm_configs FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_crm_configs ON crm_configs")
    op.execute("ALTER TABLE crm_configs DISABLE ROW LEVEL SECURITY")
