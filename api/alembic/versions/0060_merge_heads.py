"""Merge migration heads 0057, 0058, 0059

Revision ID: 0060
Revises: 0057, 0058, 0059
Create Date: 2026-03-02
"""
from alembic import op  # noqa: F401

revision = "0060"
down_revision = ("0057", "0058", "0059")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
