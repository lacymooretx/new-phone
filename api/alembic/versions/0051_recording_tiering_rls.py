"""Enable RLS on recording_tier_configs table

Revision ID: 0051
Revises: 0050
Create Date: 2026-03-01
"""

from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE recording_tier_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_recording_tier_configs ON recording_tier_configs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON recording_tier_configs TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON recording_tier_configs FROM new_phone_app")
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_recording_tier_configs ON recording_tier_configs"
    )
    op.execute("ALTER TABLE recording_tier_configs DISABLE ROW LEVEL SECURITY")
