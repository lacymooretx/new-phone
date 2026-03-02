"""Add performance indexes for commonly queried columns

Revision ID: 0056
Revises: 0055
Create Date: 2026-03-02
"""

from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None

# (index_name, table_name, columns)
_INDEXES = [
    # CDR lookups by extension, time range, caller/called number
    ("ix_call_detail_records_extension_id", "call_detail_records", ["extension_id"]),
    ("ix_call_detail_records_start_time", "call_detail_records", ["start_time"]),
    ("ix_call_detail_records_caller_number", "call_detail_records", ["caller_number"]),
    ("ix_call_detail_records_called_number", "call_detail_records", ["called_number"]),
    # Voicemail message queries by box and creation date
    ("ix_voicemail_messages_voicemail_box_id", "voicemail_messages", ["voicemail_box_id"]),
    ("ix_voicemail_messages_created_at", "voicemail_messages", ["created_at"]),
    # Recording queries by CDR and creation date
    ("ix_recordings_cdr_id", "recordings", ["cdr_id"]),
    ("ix_recordings_created_at", "recordings", ["created_at"]),
    # Audit log queries by user, time, and action type
    ("ix_audit_logs_user_id", "audit_logs", ["user_id"]),
    ("ix_audit_logs_created_at", "audit_logs", ["created_at"]),
    ("ix_audit_logs_action", "audit_logs", ["action"]),
]


def upgrade() -> None:
    for idx_name, table, columns in _INDEXES:
        op.create_index(idx_name, table, columns, if_not_exists=True)


def downgrade() -> None:
    for idx_name, table, _columns in reversed(_INDEXES):
        op.drop_index(idx_name, table_name=table, if_exists=True)
