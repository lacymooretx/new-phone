"""RLS on follow_me, GRANTs on follow_me_destinations and audit_logs

Revision ID: 0015
Revises: 0014
Create Date: 2026-02-26
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RLS on follow_me (tenant-scoped)
    op.execute("ALTER TABLE follow_me ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_follow_me ON follow_me
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON follow_me TO new_phone_app")

    # follow_me_destinations has no tenant_id — access through parent FK
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON follow_me_destinations TO new_phone_app")

    # audit_logs: INSERT + SELECT only (immutability enforced at DB level)
    # Revoke defaults first, then grant only what's needed
    op.execute("REVOKE ALL ON audit_logs FROM new_phone_app")
    op.execute("GRANT INSERT, SELECT ON audit_logs TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON audit_logs FROM new_phone_app")
    op.execute("REVOKE ALL ON follow_me_destinations FROM new_phone_app")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_follow_me ON follow_me")
    op.execute("ALTER TABLE follow_me DISABLE ROW LEVEL SECURITY")
