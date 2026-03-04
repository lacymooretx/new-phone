"""Seed Yealink T-series phone models into phone_models table.

Revision ID: 0064
Revises: 0063
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

# Yealink T-series specifications
YEALINK_MODELS = [
    {
        "manufacturer": "Yealink",
        "model_name": "T58W",
        "model_family": "yealink-t-series",
        "max_line_keys": 16,
        "max_expansion_keys": 40,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T58W-*.rom",
        "notes": "Smart media phone, 7-inch color touchscreen, Android-based",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T54W",
        "model_family": "yealink-t-series",
        "max_line_keys": 16,
        "max_expansion_keys": 40,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T54W-*.rom",
        "notes": "Prime business phone, 4.3-inch color LCD",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T53W",
        "model_family": "yealink-t-series",
        "max_line_keys": 12,
        "max_expansion_keys": 40,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T53W-*.rom",
        "notes": "Prime business phone, 3.7-inch color LCD",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T46U",
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
        "firmware_pattern": "T46U-*.rom",
        "notes": "Ultra-elegant business phone, 4.3-inch color LCD, dual USB",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T43U",
        "model_family": "yealink-t-series",
        "max_line_keys": 12,
        "max_expansion_keys": 40,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T43U-*.rom",
        "notes": "Business phone, 3.7-inch color LCD, dual USB",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T33G",
        "model_family": "yealink-t-series",
        "max_line_keys": 4,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": True,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T33G-*.rom",
        "notes": "Entry-level color screen IP phone, 4 line keys",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T31G",
        "model_family": "yealink-t-series",
        "max_line_keys": 2,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": False,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "T31G-*.rom",
        "notes": "Entry-level 2-line IP phone with gigabit",
    },
    {
        "manufacturer": "Yealink",
        "model_name": "T31P",
        "model_family": "yealink-t-series",
        "max_line_keys": 2,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": False,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": False,
        "firmware_pattern": "T31P-*.rom",
        "notes": "Entry-level 2-line IP phone, 10/100 Ethernet",
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

    op.bulk_insert(phone_models, YEALINK_MODELS)


def downgrade() -> None:
    op.execute(
        "DELETE FROM phone_models WHERE manufacturer = 'Yealink' AND model_family = 'yealink-t-series'"
    )
