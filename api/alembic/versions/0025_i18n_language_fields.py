"""Add language fields to users and tenants

Revision ID: 0025
Revises: 0024
Create Date: 2026-02-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(10), nullable=False, server_default="en"))
    op.add_column("tenants", sa.Column("default_language", sa.String(10), nullable=False, server_default="en"))


def downgrade() -> None:
    op.drop_column("tenants", "default_language")
    op.drop_column("users", "language")
