"""RLS policies + GRANTs for telephony_provider_configs

Revision ID: 0062
Revises: 0061
Create Date: 2026-03-03

MSP rows (tenant_id IS NULL) are visible only when no tenant context is set
(i.e. admin/MSP sessions). Tenant rows follow the standard tenant isolation
pattern. The admin DB user bypasses RLS as usual.
"""

from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE telephony_provider_configs ENABLE ROW LEVEL SECURITY"
    )

    # Tenant rows: standard tenant isolation
    op.execute("""
        CREATE POLICY tenant_isolation_telephony_provider_configs
        ON telephony_provider_configs
        USING (
            CASE
                WHEN tenant_id IS NOT NULL THEN
                    tenant_id = current_setting('app.current_tenant', true)::uuid
                ELSE
                    current_setting('app.current_tenant', true) IS NULL
                    OR current_setting('app.current_tenant', true) = ''
            END
        )
    """)

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON telephony_provider_configs TO new_phone_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_telephony_provider_configs "
        "ON telephony_provider_configs"
    )
    op.execute(
        "ALTER TABLE telephony_provider_configs DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "REVOKE ALL ON telephony_provider_configs FROM new_phone_app"
    )
