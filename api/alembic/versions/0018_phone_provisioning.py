"""Phase 30: phone_models, devices, device_keys tables for phone provisioning

Revision ID: 0018
Revises: 0017
Create Date: 2026-02-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── phone_models (global reference, no tenant scope) ──
    op.create_table(
        "phone_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("manufacturer", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("model_family", sa.String(50), nullable=False),
        sa.Column("max_line_keys", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("max_expansion_keys", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("max_expansion_modules", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("has_color_screen", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("has_wifi", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("has_bluetooth", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("has_expansion_port", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("has_poe", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("has_gigabit", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("firmware_pattern", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_phone_models_manufacturer", "phone_models", ["manufacturer"])

    # ── devices (tenant-scoped) ──
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mac_address", sa.String(12), nullable=False, unique=True),
        sa.Column("phone_model_id", UUID(as_uuid=True), sa.ForeignKey("phone_models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("extension_id", UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("last_provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_config_hash", sa.String(64), nullable=True),
        sa.Column("provisioning_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_devices_extension_id", "devices", ["extension_id"])

    # ── device_keys (tenant-scoped) ──
    op.create_table(
        "device_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("key_section", sa.String(20), nullable=False),
        sa.Column("key_index", sa.Integer, nullable=False),
        sa.Column("key_type", sa.String(20), nullable=False, server_default=sa.text("'none'")),
        sa.Column("label", sa.String(50), nullable=True),
        sa.Column("value", sa.String(100), nullable=True),
        sa.Column("line", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("device_id", "key_section", "key_index", name="uq_device_key_slot"),
    )


def downgrade() -> None:
    op.drop_table("device_keys")
    op.drop_table("devices")
    op.drop_table("phone_models")
