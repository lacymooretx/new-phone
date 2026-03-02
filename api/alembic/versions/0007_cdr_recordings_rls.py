"""Enable RLS on CDR and recordings tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-02-26
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "call_detail_records",
    "recordings",
]


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
