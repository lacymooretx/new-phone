import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.audio_prompt import PromptCategory


class AudioPromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: PromptCategory = PromptCategory.GENERAL
    site_id: uuid.UUID | None = None


class AudioPromptResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    category: str
    storage_path: str | None
    storage_bucket: str | None
    file_size_bytes: int
    duration_seconds: int
    format: str
    sample_rate: int
    sha256_hash: str | None
    local_path: str | None
    site_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AudioPromptPlaybackResponse(BaseModel):
    url: str
    expires_in_seconds: int = 300
