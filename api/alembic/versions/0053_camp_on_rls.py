"""Enable RLS on camp_on_configs and camp_on_requests tables

Revision ID: 0053
Revises: 0052
Create Date: 2026-03-01
"""

from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # camp_on_configs
    op.execute("ALTER TABLE camp_on_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_camp_on_configs ON camp_on_configs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON camp_on_configs TO new_phone_app")

    # camp_on_requests
    op.execute("ALTER TABLE camp_on_requests ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_camp_on_requests ON camp_on_requests
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON camp_on_requests TO new_phone_app")


def downgrade() -> None:
    # camp_on_requests
    op.execute("REVOKE ALL ON camp_on_requests FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_camp_on_requests ON camp_on_requests")
    op.execute("ALTER TABLE camp_on_requests DISABLE ROW LEVEL SECURITY")

    # camp_on_configs
    op.execute("REVOKE ALL ON camp_on_configs FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_camp_on_configs ON camp_on_configs")
    op.execute("ALTER TABLE camp_on_configs DISABLE ROW LEVEL SECURITY")
