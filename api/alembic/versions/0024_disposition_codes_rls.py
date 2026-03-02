"""RLS policies + GRANTs for disposition code tables

Revision ID: 0024
Revises: 0023
Create Date: 2026-02-27
"""

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # disposition_code_lists
    op.execute("ALTER TABLE disposition_code_lists ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_disposition_code_lists ON disposition_code_lists
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON disposition_code_lists TO new_phone_app")

    # disposition_codes
    op.execute("ALTER TABLE disposition_codes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_disposition_codes ON disposition_codes
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON disposition_codes TO new_phone_app")


def downgrade() -> None:
    for table in ["disposition_codes", "disposition_code_lists"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
