"""Seed Yealink T48S phone model into phone_models table.

Revision ID: 0065
Revises: 0064
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None

YEALINK_T48S = [
    {
        "manufacturer": "Yealink",
        "model_name": "T48S",
        "model_family": "yealink-t-series",
        "max_line_keys": 16,
        "max_expansion_keys": 40,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T48S-*.rom",
        "notes": "Ultra-elegant touchscreen IP phone, 7-inch color touch display",
    },
]


def upgrade() -> None:
    phone_models = sa.table(
        "phone_models",
        sa.column("manufacturer", sa.String),
        sa.column("model_name", sa.String),
        sa.column("model_family", sa.String),
        sa.column("max_line_keys", sa.Integer),
        sa.column("max_expansion_keys", sa.Integer),
        sa.column("max_expansion_modules", sa.Integer),
        sa.column("has_color_screen", sa.Boolean),
        sa.column("has_wifi", sa.Boolean),
        sa.column("has_bluetooth", sa.Boolean),
        sa.column("has_expansion_port", sa.Boolean),
        sa.column("has_poe", sa.Boolean),
        sa.column("has_gigabit", sa.Boolean),
        sa.column("firmware_pattern", sa.String),
        sa.column("notes", sa.Text),
    )

    op.bulk_insert(phone_models, YEALINK_T48S)


def downgrade() -> None:
    op.execute(
        "DELETE FROM phone_models WHERE manufacturer = 'Yealink' AND model_name = 'T48S'"
    )
