"""Conference bridges, page groups, page group members, pickup_group on extensions

Revision ID: 0012
Revises: 0011
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Conference Bridges ──
    op.create_table(
        "conference_bridges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("room_number", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("max_participants", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("participant_pin", sa.String(20), nullable=True),
        sa.Column("moderator_pin", sa.String(20), nullable=True),
        sa.Column("wait_for_moderator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("announce_join_leave", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("moh_prompt_id", UUID(as_uuid=True), sa.ForeignKey("audio_prompts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("record_conference", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("muted_on_join", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conference_bridges_tenant", "conference_bridges", ["tenant_id"])
    op.create_index("ix_conference_bridges_tenant_name", "conference_bridges", ["tenant_id", "name"], unique=True)
    op.create_index("ix_conference_bridges_tenant_room", "conference_bridges", ["tenant_id", "room_number"], unique=True)

    # ── Page Groups ──
    op.create_table(
        "page_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("page_number", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("page_mode", sa.String(10), nullable=False, server_default="one_way"),
        sa.Column("timeout", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_page_groups_tenant", "page_groups", ["tenant_id"])
    op.create_index("ix_page_groups_tenant_name", "page_groups", ["tenant_id", "name"], unique=True)
    op.create_index("ix_page_groups_tenant_number", "page_groups", ["tenant_id", "page_number"], unique=True)

    # ── Page Group Members ──
    op.create_table(
        "page_group_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("page_group_id", UUID(as_uuid=True), sa.ForeignKey("page_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_id", UUID(as_uuid=True), sa.ForeignKey("extensions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_page_group_members_group_ext", "page_group_members", ["page_group_id", "extension_id"], unique=True)
    op.create_index("ix_page_group_members_group_pos", "page_group_members", ["page_group_id", "position"])

    # ── Pickup group on extensions ──
    op.add_column("extensions", sa.Column("pickup_group", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("extensions", "pickup_group")
    op.drop_table("page_group_members")
    op.drop_table("page_groups")
    op.drop_table("conference_bridges")
