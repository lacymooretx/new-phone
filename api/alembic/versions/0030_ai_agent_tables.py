"""AI Voice Agent tables — provider configs, contexts, conversations, tool definitions

Revision ID: 0030
Revises: 0029
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ai_agent_provider_configs (per-tenant encrypted provider API keys) ---
    op.create_table(
        "ai_agent_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("api_key_encrypted", sa.Text, nullable=True),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("extra_config", postgresql.JSONB, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "provider_name", name="uq_ai_provider_tenant_name"),
    )

    # --- ai_agent_contexts (agent personality/behavior per tenant) ---
    op.create_table(
        "ai_agent_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("greeting", sa.Text, nullable=False),
        sa.Column("provider_mode", sa.String(20), nullable=False),
        sa.Column("monolithic_provider", sa.String(50), nullable=True),
        sa.Column("pipeline_stt", sa.String(50), nullable=True),
        sa.Column("pipeline_llm", sa.String(50), nullable=True),
        sa.Column("pipeline_tts", sa.String(50), nullable=True),
        sa.Column("pipeline_options", postgresql.JSONB, nullable=True),
        sa.Column("voice_id", sa.String(100), nullable=True),
        sa.Column(
            "language",
            sa.String(10),
            nullable=False,
            server_default="en-US",
        ),
        sa.Column(
            "barge_in_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "barge_in_sensitivity",
            sa.String(20),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "silence_timeout_ms",
            sa.Integer,
            nullable=False,
            server_default=sa.text("5000"),
        ),
        sa.Column(
            "max_call_duration_seconds",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1800"),
        ),
        sa.Column("available_tools", postgresql.JSONB, nullable=True),
        sa.Column("escalation_rules", postgresql.JSONB, nullable=True),
        sa.Column("knowledge_base", sa.Text, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_ai_context_tenant_name"),
    )

    # --- ai_agent_conversations (conversation log) ---
    op.create_table(
        "ai_agent_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "context_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_agent_contexts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("call_id", sa.String(100), nullable=True, index=True),
        sa.Column(
            "cdr_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_detail_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("caller_number", sa.String(50), nullable=False),
        sa.Column("caller_name", sa.String(200), nullable=True),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("transcript", postgresql.JSONB, nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("outcome", sa.String(50), nullable=False),
        sa.Column("transferred_to", sa.String(100), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=False),
        sa.Column(
            "turn_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "barge_in_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("latency_metrics", postgresql.JSONB, nullable=True),
        sa.Column("provider_cost_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- ai_agent_tool_definitions (custom webhook tools) ---
    op.create_table(
        "ai_agent_tool_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("parameters_schema", postgresql.JSONB, nullable=False),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column(
            "webhook_method",
            sa.String(10),
            nullable=False,
            server_default="POST",
        ),
        sa.Column("webhook_headers_encrypted", sa.Text, nullable=True),
        sa.Column("mcp_server_url", sa.String(500), nullable=True),
        sa.Column(
            "max_execution_time",
            sa.Integer,
            nullable=False,
            server_default=sa.text("30"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_ai_tool_tenant_name"),
    )


def downgrade() -> None:
    op.drop_table("ai_agent_tool_definitions")
    op.drop_table("ai_agent_conversations")
    op.drop_table("ai_agent_contexts")
    op.drop_table("ai_agent_provider_configs")
