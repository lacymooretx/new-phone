"""Create emergency & physical security integration tables

Revision ID: 0046
Revises: 0045
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── security_configs (one per tenant) ──
    op.create_table(
        "security_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("panic_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("silent_intercom_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("panic_feature_code", sa.String(20), nullable=False, server_default="*0911"),
        sa.Column("emergency_allcall_code", sa.String(20), nullable=False, server_default="*0999"),
        sa.Column("silent_intercom_max_seconds", sa.Integer, nullable=False, server_default="300"),
        sa.Column("auto_dial_911", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_security_configs_tenant_id", "security_configs", ["tenant_id"])

    # ── panic_notification_targets ──
    op.create_table(
        "panic_notification_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "security_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("security_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_value", sa.String(500), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_panic_notification_targets_tenant_id", "panic_notification_targets", ["tenant_id"]
    )

    # ── panic_alerts (immutable event log) ──
    op.create_table(
        "panic_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triggered_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "triggered_from_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger_source", sa.String(20), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("location_building", sa.String(255), nullable=True),
        sa.Column("location_floor", sa.String(100), nullable=True),
        sa.Column("location_description", sa.String(500), nullable=True),
        sa.Column("auto_911_dialed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "acknowledged_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_panic_alerts_tenant_id", "panic_alerts", ["tenant_id"])

    # ── silent_intercom_sessions (immutable audit trail) ──
    op.create_table(
        "silent_intercom_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "initiated_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fs_uuid", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("max_duration_seconds", sa.Integer, nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ended_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_silent_intercom_sessions_tenant_id", "silent_intercom_sessions", ["tenant_id"]
    )

    # ── door_stations (extension wrapper) ──
    op.create_table(
        "door_stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("manufacturer", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("unlock_url", sa.String(500), nullable=True),
        sa.Column("unlock_http_method", sa.String(10), nullable=False, server_default="POST"),
        sa.Column("unlock_headers", postgresql.JSONB, nullable=True),
        sa.Column("unlock_body", sa.Text, nullable=True),
        sa.Column("unlock_dtmf_key", sa.String(5), nullable=False, server_default="#"),
        sa.Column("ring_dest_type", sa.String(20), nullable=False, server_default="ring_group"),
        sa.Column("ring_dest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_door_stations_tenant_id", "door_stations", ["tenant_id"])

    # ── door_access_logs (immutable) ──
    op.create_table(
        "door_access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "door_station_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("door_stations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "caller_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "answered_by_extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("door_unlocked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "unlocked_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cdr_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_detail_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("call_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("call_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unlock_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_door_access_logs_tenant_id", "door_access_logs", ["tenant_id"])

    # ── paging_zones ──
    op.create_table(
        "paging_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("zone_number", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_emergency", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("tenant_id", "zone_number", name="uq_paging_zones_tenant_number"),
    )
    op.create_index("ix_paging_zones_tenant_id", "paging_zones", ["tenant_id"])

    # ── paging_zone_members (junction, no tenant_id) ──
    op.create_table(
        "paging_zone_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "paging_zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paging_zones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "extension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extensions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "paging_zone_id", "extension_id", name="uq_paging_zone_members_zone_ext"
        ),
    )

    # ── building_webhooks ──
    op.create_table(
        "building_webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("secret_token", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_building_webhooks_tenant_id", "building_webhooks", ["tenant_id"])

    # ── building_webhook_actions ──
    op.create_table(
        "building_webhook_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "webhook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_webhooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type_match", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(20), nullable=False),
        sa.Column("action_config", postgresql.JSONB, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_building_webhook_actions_tenant_id", "building_webhook_actions", ["tenant_id"]
    )

    # ── building_webhook_logs (immutable) ──
    op.create_table(
        "building_webhook_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "webhook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_webhooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("source_ip", sa.String(45), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("actions_taken", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_building_webhook_logs_tenant_id", "building_webhook_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("building_webhook_logs")
    op.drop_table("building_webhook_actions")
    op.drop_table("building_webhooks")
    op.drop_table("paging_zone_members")
    op.drop_table("paging_zones")
    op.drop_table("door_access_logs")
    op.drop_table("door_stations")
    op.drop_table("silent_intercom_sessions")
    op.drop_table("panic_alerts")
    op.drop_table("panic_notification_targets")
    op.drop_table("security_configs")
