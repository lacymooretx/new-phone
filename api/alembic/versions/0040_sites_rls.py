"""Enable RLS on sites table

Revision ID: 0040
Revises: 0039
Create Date: 2026-02-28
"""

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

TABLE = "sites"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY tenant_isolation_{TABLE} ON {TABLE}
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {TABLE} TO new_phone_app")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON {TABLE} FROM new_phone_app")
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{TABLE} ON {TABLE}")
    op.execute(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY")
