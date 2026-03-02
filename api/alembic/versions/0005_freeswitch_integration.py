"""Add FreeSWITCH integration columns: encrypted_sip_password, encrypted_pin, sip_domain

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Encrypted SIP password for FreeSWITCH directory (Fernet-encrypted, reversible)
    op.add_column("extensions", sa.Column("encrypted_sip_password", sa.Text(), nullable=True))

    # Encrypted voicemail PIN for FreeSWITCH mod_voicemail (Fernet-encrypted, reversible)
    op.add_column("voicemail_boxes", sa.Column("encrypted_pin", sa.Text(), nullable=True))

    # SIP domain for FreeSWITCH directory tenant namespacing
    op.add_column("tenants", sa.Column("sip_domain", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "sip_domain")
    op.drop_column("voicemail_boxes", "encrypted_pin")
    op.drop_column("extensions", "encrypted_sip_password")
