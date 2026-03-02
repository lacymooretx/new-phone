"""CDR + recordings tables, extension recording_policy column

Revision ID: 0006
Revises: 0005
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Call Detail Records ──
    op.create_table(
        "call_detail_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", sa.String(255), nullable=False, unique=True),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("caller_number", sa.String(40), nullable=False, server_default=""),
        sa.Column("caller_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("called_number", sa.String(40), nullable=False, server_default=""),
        sa.Column("extension_id", UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("did_id", UUID(as_uuid=True), sa.ForeignKey("dids.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trunk_id", UUID(as_uuid=True), sa.ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ring_group_id", UUID(as_uuid=True), sa.ForeignKey("ring_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("disposition", sa.String(30), nullable=False),
        sa.Column("hangup_cause", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("billable_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ring_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answer_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("has_recording", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cdr_tenant_start", "call_detail_records", ["tenant_id", "start_time"])
    op.create_index("ix_cdr_tenant_extension", "call_detail_records", ["tenant_id", "extension_id"])
    op.create_index("ix_cdr_call_id", "call_detail_records", ["call_id"], unique=True)

    # ── Recordings ──
    op.create_table(
        "recordings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cdr_id", UUID(as_uuid=True), sa.ForeignKey("call_detail_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("call_id", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("storage_bucket", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("format", sa.String(10), nullable=False, server_default="wav"),
        sa.Column("sample_rate", sa.Integer(), nullable=False, server_default=sa.text("8000")),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("recording_policy", sa.String(20), nullable=False, server_default="always"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recordings_tenant_created", "recordings", ["tenant_id", "created_at"])
    op.create_index("ix_recordings_cdr_id", "recordings", ["cdr_id"])
    op.create_index("ix_recordings_call_id", "recordings", ["call_id"])

    # ── Add recording_policy to extensions ──
    op.add_column(
        "extensions",
        sa.Column("recording_policy", sa.String(20), nullable=False, server_default="never"),
    )


def downgrade() -> None:
    op.drop_column("extensions", "recording_policy")
    op.drop_table("recordings")
    op.drop_table("call_detail_records")
