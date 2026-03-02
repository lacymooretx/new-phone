"""SSO foundation — sso_providers, sso_role_mappings, user_sso_links tables + users auth_method

Revision ID: 0026
Revises: 0025
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- sso_providers ---
    op.create_table(
        "sso_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text, nullable=False),
        sa.Column("issuer_url", sa.String(500), nullable=False),
        sa.Column("discovery_url", sa.String(500), nullable=False),
        sa.Column("scopes", sa.String(500), nullable=False, server_default="openid email profile"),
        sa.Column("auto_provision", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("default_role", sa.String(30), nullable=False, server_default="tenant_user"),
        sa.Column("enforce_sso", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
    )

    # --- sso_role_mappings ---
    op.create_table(
        "sso_role_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "sso_provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sso_providers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("external_group_id", sa.String(255), nullable=False),
        sa.Column("external_group_name", sa.String(255), nullable=True),
        sa.Column("pbx_role", sa.String(30), nullable=False),
        sa.UniqueConstraint(
            "sso_provider_id",
            "external_group_id",
            name="uq_sso_role_mapping_provider_group",
        ),
    )

    # --- user_sso_links ---
    op.create_table(
        "user_sso_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "sso_provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sso_providers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("external_email", sa.String(320), nullable=False),
        sa.Column("last_sso_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "sso_provider_id",
            "external_user_id",
            name="uq_user_sso_link_provider_ext_user",
        ),
    )

    # --- users table modifications ---
    op.add_column(
        "users",
        sa.Column("auth_method", sa.String(20), nullable=False, server_default="local"),
    )
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    # Reverse users table modifications
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.drop_column("users", "auth_method")

    # Drop tables in reverse dependency order
    op.drop_table("user_sso_links")
    op.drop_table("sso_role_mappings")
    op.drop_table("sso_providers")
