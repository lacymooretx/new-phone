import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RecordingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    cdr_id: uuid.UUID | None
    call_id: str
    storage_path: str | None
    storage_bucket: str | None
    file_size_bytes: int
    duration_seconds: int
    format: str
    sample_rate: int
    sha256_hash: str | None
    recording_policy: str
    is_active: bool
    created_at: datetime
    storage_tier: str = "hot"
    archived_at: datetime | None = None
    legal_hold: bool = False
    retrieval_requested_at: datetime | None = None
    retrieval_expires_at: datetime | None = None
    retention_expires_at: datetime | None = None


class RecordingPlaybackResponse(BaseModel):
    url: str
    expires_in_seconds: int = 300


class RecordingFilter(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    call_id: str | None = None
    cdr_id: uuid.UUID | None = None
    storage_tier: str | None = None
    legal_hold: bool | None = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)
