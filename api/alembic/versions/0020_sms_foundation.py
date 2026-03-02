"""SMS foundation tables — provider configs, conversations, messages, notes, opt-outs

Revision ID: 0020
Revises: 0019
Create Date: 2026-02-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sms_provider_configs ─────────────────────────────────────────
    op.create_table(
        "sms_provider_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("encrypted_credentials", sa.Text, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sms_provider_configs_tenant_id", "sms_provider_configs", ["tenant_id"])
    op.create_index("ix_sms_provider_configs_tenant_default", "sms_provider_configs", ["tenant_id", "is_default"])

    # ── conversations ────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("did_id", UUID(as_uuid=True), sa.ForeignKey("dids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("remote_number", sa.String(20), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False, server_default=sa.text("'sms'")),
        sa.Column("state", sa.String(20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("assigned_to_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("queue_id", UUID(as_uuid=True), sa.ForeignKey("queues.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_tenant_state", "conversations", ["tenant_id", "state"])
    op.create_index("ix_conversations_tenant_did", "conversations", ["tenant_id", "did_id"])
    op.create_index("ix_conversations_tenant_remote", "conversations", ["tenant_id", "remote_number"])
    op.create_unique_constraint("uq_conversation_tenant_did_remote", "conversations", ["tenant_id", "did_id", "remote_number"])

    # ── messages ─────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("from_number", sa.String(20), nullable=False),
        sa.Column("to_number", sa.String(20), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("media_urls", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("provider", sa.String(20), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("sent_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("segments", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index("ix_messages_provider_message_id", "messages", ["provider_message_id"])

    # ── conversation_notes ───────────────────────────────────────────
    op.create_table(
        "conversation_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversation_notes_conversation_id", "conversation_notes", ["conversation_id"])

    # ── sms_opt_outs ─────────────────────────────────────────────────
    op.create_table(
        "sms_opt_outs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("did_id", UUID(as_uuid=True), sa.ForeignKey("dids.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opted_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_opted_out", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sms_opt_outs_tenant_id", "sms_opt_outs", ["tenant_id"])
    op.create_unique_constraint("uq_opt_out_tenant_did_phone", "sms_opt_outs", ["tenant_id", "did_id", "phone_number"])

    # ── Add sms_enabled to dids ──────────────────────────────────────
    op.add_column("dids", sa.Column("sms_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("dids", "sms_enabled")
    op.drop_table("sms_opt_outs")
    op.drop_table("conversation_notes")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("sms_provider_configs")
