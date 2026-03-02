import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RecordingTierConfigCreate(BaseModel):
    hot_tier_days: int = Field(90, ge=1, le=3650)
    cold_tier_retention_days: int = Field(365, ge=1, le=3650)
    retrieval_cache_days: int = Field(7, ge=1, le=90)
    auto_tier_enabled: bool = True
    auto_delete_enabled: bool = False


class RecordingTierConfigUpdate(BaseModel):
    hot_tier_days: int | None = Field(None, ge=1, le=3650)
    cold_tier_retention_days: int | None = Field(None, ge=1, le=3650)
    retrieval_cache_days: int | None = Field(None, ge=1, le=90)
    auto_tier_enabled: bool | None = None
    auto_delete_enabled: bool | None = None


class RecordingTierConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    hot_tier_days: int
    cold_tier_retention_days: int
    retrieval_cache_days: int
    auto_tier_enabled: bool
    auto_delete_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RecordingRetrievalResponse(BaseModel):
    recording_id: uuid.UUID
    status: str
    message: str


class RecordingStorageStats(BaseModel):
    hot_count: int = 0
    hot_bytes: int = 0
    cold_count: int = 0
    cold_bytes: int = 0
    legal_hold_count: int = 0
    total_bytes: int = 0


class RecordingLegalHoldRequest(BaseModel):
    recording_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)
    hold: bool


class RecordingLegalHoldResponse(BaseModel):
    updated_count: int
