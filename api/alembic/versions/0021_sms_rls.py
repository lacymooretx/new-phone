"""RLS policies + GRANTs for SMS tables

Revision ID: 0021
Revises: 0020
Create Date: 2026-02-27
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # sms_provider_configs
    op.execute("ALTER TABLE sms_provider_configs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_sms_provider_configs ON sms_provider_configs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON sms_provider_configs TO new_phone_app")

    # conversations
    op.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_conversations ON conversations
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conversations TO new_phone_app")

    # messages
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_messages ON messages
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON messages TO new_phone_app")

    # conversation_notes
    op.execute("ALTER TABLE conversation_notes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_conversation_notes ON conversation_notes
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conversation_notes TO new_phone_app")

    # sms_opt_outs
    op.execute("ALTER TABLE sms_opt_outs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_sms_opt_outs ON sms_opt_outs
            USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON sms_opt_outs TO new_phone_app")


def downgrade() -> None:
    for table in ["sms_opt_outs", "conversation_notes", "messages", "conversations", "sms_provider_configs"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
