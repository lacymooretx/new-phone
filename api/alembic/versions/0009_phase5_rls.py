"""Enable RLS on Phase 5 tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-02-26
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "audio_prompts",
    "voicemail_messages",
    "time_conditions",
    "ivr_menus",
]


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")

    # ivr_menu_options has no tenant_id — access through parent FK
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ivr_menu_options TO new_phone_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON ivr_menu_options FROM new_phone_app")
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
