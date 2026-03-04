"""Seed Sangoma P-series phone models into phone_models table.

Revision ID: 0063
Revises: 0062
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None

# Sangoma P-series specifications
SANGOMA_MODELS = [
    {
        "manufacturer": "Sangoma",
        "model_name": "P310",
        "model_family": "sangoma-p-series",
        "max_line_keys": 2,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": False,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": False,
        "firmware_pattern": "p310-*.fw",
        "notes": "Entry-level 2-line IP phone",
    },
    {
        "manufacturer": "Sangoma",
        "model_name": "P315",
        "model_family": "sangoma-p-series",
        "max_line_keys": 4,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "p315-*.fw",
        "notes": "Mid-range 4-line color IP phone with WiFi/BT",
    },
    {
        "manufacturer": "Sangoma",
        "model_name": "P320",
        "model_family": "sangoma-p-series",
        "max_line_keys": 8,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": True,
        "has_wifi": False,
        "has_bluetooth": False,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "p320-*.fw",
        "notes": "Mid-range 8-line color IP phone",
    },
    {
        "manufacturer": "Sangoma",
        "model_name": "P325",
        "model_family": "sangoma-p-series",
        "max_line_keys": 8,
        "max_expansion_keys": 0,
        "max_expansion_modules": 0,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": False,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "p325-*.fw",
        "notes": "Mid-range 8-line color IP phone with WiFi/BT",
    },
    {
        "manufacturer": "Sangoma",
        "model_name": "P330",
        "model_family": "sangoma-p-series",
        "max_line_keys": 12,
        "max_expansion_keys": 40,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "p330-*.fw",
        "notes": "High-end 12-line color IP phone with expansion support",
    },
    {
        "manufacturer": "Sangoma",
        "model_name": "P370",
        "model_family": "sangoma-p-series",
        "max_line_keys": 16,
        "max_expansion_keys": 60,
        "max_expansion_modules": 3,
        "has_color_screen": True,
        "has_wifi": True,
        "has_bluetooth": True,
        "has_expansion_port": True,
        "has_poe": True,
        "has_gigabit": True,
        "firmware_pattern": "p370-*.fw",
        "notes": "Executive 16-line touchscreen IP phone with expansion support",
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

    op.bulk_insert(phone_models, SANGOMA_MODELS)


def downgrade() -> None:
    op.execute(
        "DELETE FROM phone_models WHERE manufacturer = 'Sangoma' AND model_family = 'sangoma-p-series'"
    )
