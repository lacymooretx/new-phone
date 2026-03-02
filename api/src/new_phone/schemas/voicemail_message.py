import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.voicemail_message import VMFolder


class VoicemailMessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    voicemail_box_id: uuid.UUID
    caller_number: str
    caller_name: str
    duration_seconds: int
    storage_path: str | None
    storage_bucket: str | None
    file_size_bytes: int
    format: str
    sha256_hash: str | None
    is_read: bool
    is_urgent: bool
    folder: str
    call_id: str | None
    email_sent: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VoicemailMessageUpdate(BaseModel):
    is_read: bool | None = None
    folder: VMFolder | None = None


class VoicemailMessagePlaybackResponse(BaseModel):
    url: str
    expires_in_seconds: int = 300


class VoicemailMessageFilter(BaseModel):
    folder: VMFolder | None = None
    is_read: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class VoicemailMessageSummaryResponse(BaseModel):
    voicemail_box_id: uuid.UUID
    mailbox_number: str
    unread_count: int


class VoicemailForwardRequest(BaseModel):
    target_box_id: uuid.UUID
