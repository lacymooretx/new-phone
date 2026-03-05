"""Expand phone_app_configs with provisioning fields.

Revision ID: 0066
Revises: 0065
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("phone_app_configs", sa.Column("timezone", sa.String(50), nullable=False, server_default="America/Chicago"))
    op.add_column("phone_app_configs", sa.Column("language", sa.String(30), nullable=False, server_default="English"))
    op.add_column("phone_app_configs", sa.Column("date_format", sa.String(5), nullable=False, server_default="2"))
    op.add_column("phone_app_configs", sa.Column("time_format", sa.String(5), nullable=False, server_default="1"))
    op.add_column("phone_app_configs", sa.Column("encrypted_phone_admin_password", sa.String(500), nullable=True))
    op.add_column("phone_app_configs", sa.Column("logo_url", sa.String(500), nullable=True))
    op.add_column("phone_app_configs", sa.Column("ringtone", sa.String(50), nullable=False, server_default="Ring1.wav"))
    op.add_column("phone_app_configs", sa.Column("backlight_time", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("phone_app_configs", sa.Column("screensaver_type", sa.String(5), nullable=False, server_default="2"))
    op.add_column("phone_app_configs", sa.Column("firmware_url", sa.String(500), nullable=True))
    op.add_column("phone_app_configs", sa.Column("codec_priority", sa.String(200), nullable=False, server_default="PCMU,PCMA,G722,G729,opus"))
    op.add_column("phone_app_configs", sa.Column("pickup_code", sa.String(10), nullable=False, server_default="*8"))
    op.add_column("phone_app_configs", sa.Column("intercom_code", sa.String(10), nullable=False, server_default="*80"))
    op.add_column("phone_app_configs", sa.Column("parking_code", sa.String(10), nullable=False, server_default="*85"))
    op.add_column("phone_app_configs", sa.Column("dnd_on_code", sa.String(10), nullable=True))
    op.add_column("phone_app_configs", sa.Column("dnd_off_code", sa.String(10), nullable=True))
    op.add_column("phone_app_configs", sa.Column("fwd_unconditional_code", sa.String(10), nullable=True))
    op.add_column("phone_app_configs", sa.Column("fwd_busy_code", sa.String(10), nullable=True))
    op.add_column("phone_app_configs", sa.Column("fwd_noanswer_code", sa.String(10), nullable=True))
    op.add_column("phone_app_configs", sa.Column("dscp_sip", sa.Integer(), nullable=False, server_default="46"))
    op.add_column("phone_app_configs", sa.Column("dscp_rtp", sa.Integer(), nullable=False, server_default="46"))
    op.add_column("phone_app_configs", sa.Column("vlan_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("phone_app_configs", sa.Column("vlan_id", sa.Integer(), nullable=True))
    op.add_column("phone_app_configs", sa.Column("vlan_priority", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("phone_app_configs", sa.Column("action_urls_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    for col in [
        "action_urls_enabled", "vlan_priority", "vlan_id", "vlan_enabled",
        "dscp_rtp", "dscp_sip", "fwd_noanswer_code", "fwd_busy_code",
        "fwd_unconditional_code", "dnd_off_code", "dnd_on_code",
        "parking_code", "intercom_code", "pickup_code", "codec_priority",
        "firmware_url", "screensaver_type", "backlight_time", "ringtone",
        "logo_url", "encrypted_phone_admin_password", "time_format",
        "date_format", "language", "timezone",
    ]:
        op.drop_column("phone_app_configs", col)
