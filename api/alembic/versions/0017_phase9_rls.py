"""RLS on caller_id_rules and holiday_calendars, GRANTs for Phase 9 tables

Revision ID: 0017
Revises: 0016
Create Date: 2026-02-26
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RLS on caller_id_rules (tenant-scoped)
    op.execute("ALTER TABLE caller_id_rules ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_caller_id_rules ON caller_id_rules
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON caller_id_rules TO new_phone_app")

    # RLS on holiday_calendars (tenant-scoped)
    op.execute("ALTER TABLE holiday_calendars ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_holiday_calendars ON holiday_calendars
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON holiday_calendars TO new_phone_app")

    # holiday_entries has no tenant_id — access through parent FK
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON holiday_entries TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON holiday_entries FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_holiday_calendars ON holiday_calendars")
    op.execute("ALTER TABLE holiday_calendars DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON holiday_calendars FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_caller_id_rules ON caller_id_rules")
    op.execute("ALTER TABLE caller_id_rules DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON caller_id_rules FROM new_phone_app")
