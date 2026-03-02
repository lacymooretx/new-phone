"""Enable RLS on conference_bridges and page_groups, GRANT on page_group_members

Revision ID: 0013
Revises: 0012
Create Date: 2026-02-26
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RLS on conference_bridges (tenant-scoped)
    op.execute("ALTER TABLE conference_bridges ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_conference_bridges ON conference_bridges
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conference_bridges TO new_phone_app")

    # RLS on page_groups (tenant-scoped)
    op.execute("ALTER TABLE page_groups ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_page_groups ON page_groups
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON page_groups TO new_phone_app")

    # page_group_members has no tenant_id — access through parent FK
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON page_group_members TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON page_group_members FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_page_groups ON page_groups")
    op.execute("ALTER TABLE page_groups DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_conference_bridges ON conference_bridges")
    op.execute("ALTER TABLE conference_bridges DISABLE ROW LEVEL SECURITY")
