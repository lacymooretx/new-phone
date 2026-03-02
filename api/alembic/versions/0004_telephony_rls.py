"""Enable RLS on telephony tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-25
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# Tables that have tenant_id and need RLS
TENANT_TABLES = [
    "voicemail_boxes",
    "extensions",
    "sip_trunks",
    "dids",
    "inbound_routes",
    "outbound_routes",
    "ring_groups",
]

# Junction tables — no tenant_id, no RLS, but need GRANTs
JUNCTION_TABLES = [
    "outbound_route_trunks",
    "ring_group_members",
]


def upgrade() -> None:
    for table in TENANT_TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # RLS policy: app user can only see rows matching current tenant
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
        """)

        # Grant table permissions to app user
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")

    # Junction tables — just GRANTs, no RLS
    for table in JUNCTION_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO new_phone_app")


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
