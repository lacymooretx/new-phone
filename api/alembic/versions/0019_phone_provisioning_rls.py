"""RLS policies + GRANTs for phone provisioning tables

Revision ID: 0019
Revises: 0018
Create Date: 2026-02-27
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # phone_models: global reference data, no RLS — just GRANT read to app user
    op.execute("GRANT SELECT ON phone_models TO new_phone_app")

    # devices: tenant-scoped RLS
    op.execute("ALTER TABLE devices ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_devices ON devices
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON devices TO new_phone_app")

    # device_keys: tenant-scoped RLS
    op.execute("ALTER TABLE device_keys ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_device_keys ON device_keys
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON device_keys TO new_phone_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_device_keys ON device_keys")
    op.execute("ALTER TABLE device_keys DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON device_keys FROM new_phone_app")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_devices ON devices")
    op.execute("ALTER TABLE devices DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON devices FROM new_phone_app")

    op.execute("REVOKE ALL ON phone_models FROM new_phone_app")
