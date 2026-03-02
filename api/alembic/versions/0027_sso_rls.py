"""RLS policies + GRANTs for SSO tables

Revision ID: 0027
Revises: 0026
Create Date: 2026-02-28
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- sso_providers (direct tenant_id) ---
    op.execute("ALTER TABLE sso_providers ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_sso_providers ON sso_providers
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON sso_providers TO new_phone_app")

    # --- sso_role_mappings (via sso_providers join) ---
    op.execute("ALTER TABLE sso_role_mappings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_sso_role_mappings ON sso_role_mappings
            USING (sso_provider_id IN (
                SELECT id FROM sso_providers
                WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
            ))
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON sso_role_mappings TO new_phone_app")

    # --- user_sso_links (via users join) ---
    op.execute("ALTER TABLE user_sso_links ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_user_sso_links ON user_sso_links
            USING (user_id IN (
                SELECT id FROM users
                WHERE tenant_id = current_setting('app.current_tenant', true)::uuid
            ))
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON user_sso_links TO new_phone_app")


def downgrade() -> None:
    for table in ["user_sso_links", "sso_role_mappings", "sso_providers"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
