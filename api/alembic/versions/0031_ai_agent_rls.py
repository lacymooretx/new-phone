"""RLS policies + GRANTs for AI Voice Agent tables

Revision ID: 0031
Revises: 0030
Create Date: 2026-02-28
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

_TABLES = [
    "ai_agent_provider_configs",
    "ai_agent_contexts",
    "ai_agent_conversations",
    "ai_agent_tool_definitions",
]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
