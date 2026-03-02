"""RLS policies + GRANTs for ConnectWise PSA tables

Revision ID: 0029
Revises: 0028
Create Date: 2026-02-28
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- cw_configs (direct tenant_id) ---
    op.execute("ALTER TABLE cw_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_cw_configs ON cw_configs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON cw_configs TO new_phone_app")

    # --- cw_company_mappings (via cw_configs join) ---
    op.execute("ALTER TABLE cw_company_mappings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_cw_company_mappings ON cw_company_mappings
            USING (cw_config_id IN (
                SELECT id FROM cw_configs
                WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
            ))
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON cw_company_mappings TO new_phone_app")

    # --- cw_ticket_logs (via cw_configs join) ---
    op.execute("ALTER TABLE cw_ticket_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_cw_ticket_logs ON cw_ticket_logs
            USING (cw_config_id IN (
                SELECT id FROM cw_configs
                WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
            ))
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON cw_ticket_logs TO new_phone_app")


def downgrade() -> None:
    for table in ["cw_ticket_logs", "cw_company_mappings", "cw_configs"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
