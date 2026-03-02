"""Enable RLS on workforce management tables

Revision ID: 0045
Revises: 0044
Create Date: 2026-02-28
"""

from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None

TABLES = ["wfm_shifts", "wfm_schedule_entries", "wfm_time_off_requests", "wfm_forecast_configs"]


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
