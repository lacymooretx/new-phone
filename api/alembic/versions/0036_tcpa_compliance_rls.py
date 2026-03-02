"""Enable RLS on TCPA compliance tables

Revision ID: 0036
Revises: 0035
Create Date: 2026-02-28
"""

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

STANDARD_TABLES = [
    "dnc_lists",
    "dnc_entries",
    "consent_records",
    "compliance_settings",
]


def upgrade() -> None:
    # Standard RLS for dnc_lists, dnc_entries, consent_records, compliance_settings
    for table in STANDARD_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")

    # compliance_audit_logs — immutable: SELECT + INSERT only, no UPDATE/DELETE
    op.execute("ALTER TABLE compliance_audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_compliance_audit_logs ON compliance_audit_logs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT ON compliance_audit_logs TO new_phone_app")
    # Explicitly revoke UPDATE/DELETE to enforce immutability
    op.execute("REVOKE UPDATE, DELETE ON compliance_audit_logs FROM new_phone_app")


def downgrade() -> None:
    # compliance_audit_logs
    op.execute("REVOKE ALL ON compliance_audit_logs FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_compliance_audit_logs ON compliance_audit_logs")
    op.execute("ALTER TABLE compliance_audit_logs DISABLE ROW LEVEL SECURITY")

    # Standard tables
    for table in reversed(STANDARD_TABLES):
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
