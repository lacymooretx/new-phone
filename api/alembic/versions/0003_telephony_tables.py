"""Telephony tables — voicemail, extensions, trunks, DIDs, routes, ring groups

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Voicemail Boxes ──
    op.create_table(
        "voicemail_boxes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mailbox_number", sa.String(20), nullable=False),
        sa.Column("pin_hash", sa.String(255), nullable=False),
        sa.Column("greeting_type", sa.String(20), nullable=False, server_default="default"),
        sa.Column("email_notification", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notification_email", sa.String(320), nullable=True),
        sa.Column("max_messages", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_voicemail_boxes_tenant_id", "voicemail_boxes", ["tenant_id"])
    op.create_index("ix_voicemail_boxes_tenant_mailbox", "voicemail_boxes", ["tenant_id", "mailbox_number"], unique=False)

    # ── Extensions ──
    op.create_table(
        "extensions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_number", sa.String(20), nullable=False),
        sa.Column("sip_username", sa.String(100), nullable=False),
        sa.Column("sip_password_hash", sa.String(255), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("voicemail_box_id", UUID(as_uuid=True), sa.ForeignKey("voicemail_boxes.id", ondelete="SET NULL"), nullable=True),
        # Caller ID
        sa.Column("internal_cid_name", sa.String(100), nullable=True),
        sa.Column("internal_cid_number", sa.String(20), nullable=True),
        sa.Column("external_cid_name", sa.String(100), nullable=True),
        sa.Column("external_cid_number", sa.String(20), nullable=True),
        sa.Column("emergency_cid_number", sa.String(20), nullable=True),
        # E911
        sa.Column("e911_street", sa.String(255), nullable=True),
        sa.Column("e911_city", sa.String(100), nullable=True),
        sa.Column("e911_state", sa.String(50), nullable=True),
        sa.Column("e911_zip", sa.String(20), nullable=True),
        sa.Column("e911_country", sa.String(2), nullable=True, server_default="US"),
        # Call forwarding
        sa.Column("call_forward_unconditional", sa.String(40), nullable=True),
        sa.Column("call_forward_busy", sa.String(40), nullable=True),
        sa.Column("call_forward_no_answer", sa.String(40), nullable=True),
        sa.Column("call_forward_not_registered", sa.String(40), nullable=True),
        sa.Column("call_forward_ring_time", sa.Integer(), nullable=False, server_default=sa.text("25")),
        # Features
        sa.Column("dnd_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("call_waiting", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_registrations", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("outbound_cid_mode", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("class_of_service", sa.String(20), nullable=False, server_default="domestic"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_extensions_tenant_id", "extensions", ["tenant_id"])
    op.create_index("ix_extensions_tenant_number", "extensions", ["tenant_id", "extension_number"], unique=False)
    op.create_index("ix_extensions_user_id", "extensions", ["user_id"])

    # ── SIP Trunks ──
    op.create_table(
        "sip_trunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("auth_type", sa.String(20), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default=sa.text("5061")),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("encrypted_password", sa.Text(), nullable=True),
        sa.Column("ip_acl", sa.Text(), nullable=True),
        sa.Column("codec_preferences", JSONB(), nullable=True),
        sa.Column("max_channels", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("transport", sa.String(10), nullable=False, server_default="tls"),
        sa.Column("inbound_cid_mode", sa.String(20), nullable=False, server_default="passthrough"),
        sa.Column("failover_trunk_id", UUID(as_uuid=True), sa.ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sip_trunks_tenant_id", "sip_trunks", ["tenant_id"])

    # ── DIDs ──
    op.create_table(
        "dids",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.String(20), nullable=False, unique=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_sid", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dids_tenant_id", "dids", ["tenant_id"])
    op.create_index("ix_dids_number", "dids", ["number"])

    # ── Inbound Routes ──
    op.create_table(
        "inbound_routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("did_id", UUID(as_uuid=True), sa.ForeignKey("dids.id", ondelete="SET NULL"), nullable=True),
        sa.Column("destination_type", sa.String(20), nullable=False),
        sa.Column("destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("cid_name_prefix", sa.String(50), nullable=True),
        sa.Column("time_conditions", JSONB(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inbound_routes_tenant_id", "inbound_routes", ["tenant_id"])

    # ── Outbound Routes ──
    op.create_table(
        "outbound_routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dial_pattern", sa.String(100), nullable=False),
        sa.Column("prepend_digits", sa.String(20), nullable=True),
        sa.Column("strip_digits", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cid_mode", sa.String(20), nullable=False, server_default="extension"),
        sa.Column("custom_cid", sa.String(40), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outbound_routes_tenant_id", "outbound_routes", ["tenant_id"])

    # ── Outbound Route Trunks (junction) ──
    op.create_table(
        "outbound_route_trunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("outbound_route_id", UUID(as_uuid=True), sa.ForeignKey("outbound_routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trunk_id", UUID(as_uuid=True), sa.ForeignKey("sip_trunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_outbound_route_trunks_route_id", "outbound_route_trunks", ["outbound_route_id"])

    # ── Ring Groups ──
    op.create_table(
        "ring_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_number", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ring_strategy", sa.String(20), nullable=False, server_default="simultaneous"),
        sa.Column("ring_time", sa.Integer(), nullable=False, server_default=sa.text("25")),
        sa.Column("ring_time_per_member", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("skip_busy", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("cid_passthrough", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("confirm_calls", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("failover_dest_type", sa.String(20), nullable=True),
        sa.Column("failover_dest_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ring_groups_tenant_id", "ring_groups", ["tenant_id"])
    op.create_index("ix_ring_groups_tenant_number", "ring_groups", ["tenant_id", "group_number"], unique=False)

    # ── Ring Group Members (junction) ──
    op.create_table(
        "ring_group_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ring_group_id", UUID(as_uuid=True), sa.ForeignKey("ring_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_id", UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_ring_group_members_group_id", "ring_group_members", ["ring_group_id"])


def downgrade() -> None:
    op.drop_table("ring_group_members")
    op.drop_table("ring_groups")
    op.drop_table("outbound_route_trunks")
    op.drop_table("outbound_routes")
    op.drop_table("inbound_routes")
    op.drop_table("dids")
    op.drop_table("sip_trunks")
    op.drop_table("extensions")
    op.drop_table("voicemail_boxes")
