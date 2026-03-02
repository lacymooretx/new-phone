"""Audio prompts, voicemail messages, time conditions, IVR menus

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Audio Prompts ──
    op.create_table(
        "audio_prompts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("storage_bucket", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("format", sa.String(10), nullable=False, server_default="wav"),
        sa.Column("sample_rate", sa.Integer(), nullable=False, server_default=sa.text("8000")),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("local_path", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audio_prompts_tenant_category", "audio_prompts", ["tenant_id", "category"])
    op.create_index("ix_audio_prompts_tenant_name", "audio_prompts", ["tenant_id", "name"], unique=True)

    # ── Voicemail Messages ──
    op.create_table(
        "voicemail_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("voicemail_box_id", UUID(as_uuid=True), sa.ForeignKey("voicemail_boxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("caller_number", sa.String(40), nullable=False, server_default=""),
        sa.Column("caller_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("storage_bucket", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("format", sa.String(10), nullable=False, server_default="wav"),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("folder", sa.String(20), nullable=False, server_default="new"),
        sa.Column("call_id", sa.String(255), nullable=True),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_vm_messages_box_folder", "voicemail_messages", ["voicemail_box_id", "folder"])
    op.create_index("ix_vm_messages_tenant_created", "voicemail_messages", ["tenant_id", "created_at"])
    op.create_index("ix_vm_messages_call_id", "voicemail_messages", ["call_id"])

    # ── Time Conditions ──
    op.create_table(
        "time_conditions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="America/New_York"),
        sa.Column("rules", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("match_destination_type", sa.String(20), nullable=False),
        sa.Column("match_destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("nomatch_destination_type", sa.String(20), nullable=False),
        sa.Column("nomatch_destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_time_conditions_tenant", "time_conditions", ["tenant_id"])
    op.create_index("ix_time_conditions_tenant_name", "time_conditions", ["tenant_id", "name"], unique=True)

    # ── IVR Menus ──
    op.create_table(
        "ivr_menus",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("greet_long_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("greet_short_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invalid_sound_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exit_sound_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("timeout", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("max_failures", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("max_timeouts", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("inter_digit_timeout", sa.Integer(), nullable=False, server_default=sa.text("2")),
        sa.Column("digit_len", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("exit_destination_type", sa.String(20), nullable=True),
        sa.Column("exit_destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tts_engine", sa.String(50), nullable=True),
        sa.Column("tts_voice", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ivr_menus_tenant", "ivr_menus", ["tenant_id"])
    op.create_index("ix_ivr_menus_tenant_name", "ivr_menus", ["tenant_id", "name"], unique=True)

    # ── IVR Menu Options ──
    op.create_table(
        "ivr_menu_options",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ivr_menu_id", UUID(as_uuid=True), sa.ForeignKey("ivr_menus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("digits", sa.String(10), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("action_target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action_target_value", sa.String(255), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_ivr_menu_options_menu_digits", "ivr_menu_options", ["ivr_menu_id", "digits"], unique=True)


def downgrade() -> None:
    op.drop_table("ivr_menu_options")
    op.drop_table("ivr_menus")
    op.drop_table("time_conditions")
    op.drop_table("voicemail_messages")
    op.drop_table("audio_prompts")
