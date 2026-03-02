"""Enable RLS on queues table, GRANT on queue_members

Revision ID: 0011
Revises: 0010
Create Date: 2026-02-26
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RLS on queues (tenant-scoped)
    op.execute("ALTER TABLE queues ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_queues ON queues
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON queues TO new_phone_app")

    # queue_members has no tenant_id — access through parent FK
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON queue_members TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON queue_members FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_queues ON queues")
    op.execute("ALTER TABLE queues DISABLE ROW LEVEL SECURITY")
