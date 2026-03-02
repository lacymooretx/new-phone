"""Enable RLS on emergency & physical security tables

Revision ID: 0047
Revises: 0046
Create Date: 2026-03-01
"""

from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None

# Standard RLS: SELECT, INSERT, UPDATE, DELETE
STANDARD_TABLES = [
    "security_configs",
    "panic_notification_targets",
    "panic_alerts",
    "silent_intercom_sessions",
    "door_stations",
    "paging_zones",
    "building_webhooks",
    "building_webhook_actions",
]

# Immutable tables: SELECT + INSERT only, no UPDATE/DELETE
IMMUTABLE_TABLES = [
    "door_access_logs",
    "building_webhook_logs",
]


def upgrade() -> None:
    # Standard RLS tables
    for table in STANDARD_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")

    # Immutable tables: RLS + INSERT/SELECT only
    for table in IMMUTABLE_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)
        op.execute(f"GRANT SELECT, INSERT ON {table} TO new_phone_app")
        # Explicitly revoke UPDATE/DELETE to enforce immutability
        op.execute(f"REVOKE UPDATE, DELETE ON {table} FROM new_phone_app")

    # paging_zone_members has no tenant_id — access through parent FK
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON paging_zone_members TO new_phone_app")


def downgrade() -> None:
    # paging_zone_members
    op.execute("REVOKE ALL ON paging_zone_members FROM new_phone_app")

    # Immutable tables
    for table in reversed(IMMUTABLE_TABLES):
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Standard tables
    for table in reversed(STANDARD_TABLES):
        op.execute(f"REVOKE ALL ON {table} FROM new_phone_app")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
