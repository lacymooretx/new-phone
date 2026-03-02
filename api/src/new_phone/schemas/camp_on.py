import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CampOnConfigCreate(BaseModel):
    enabled: bool = True
    feature_code: str = Field("*88", max_length=20)
    timeout_minutes: int = Field(30, ge=1, le=1440)
    max_camp_ons_per_target: int = Field(5, ge=1, le=50)
    callback_retry_delay_seconds: int = Field(30, ge=5, le=300)


class CampOnConfigUpdate(BaseModel):
    enabled: bool | None = None
    feature_code: str | None = Field(None, max_length=20)
    timeout_minutes: int | None = Field(None, ge=1, le=1440)
    max_camp_ons_per_target: int | None = Field(None, ge=1, le=50)
    callback_retry_delay_seconds: int | None = Field(None, ge=5, le=300)


class CampOnConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    enabled: bool
    feature_code: str
    timeout_minutes: int
    max_camp_ons_per_target: int
    callback_retry_delay_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CampOnCreateRequest(BaseModel):
    caller_extension_number: str = Field(..., max_length=20)
    target_extension_number: str = Field(..., max_length=20)
    reason: str = Field(..., max_length=20)
    original_call_id: str | None = Field(None, max_length=255)


class CampOnRequestResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    caller_extension_id: uuid.UUID
    target_extension_id: uuid.UUID
    caller_extension_number: str
    target_extension_number: str
    reason: str
    status: str
    callback_attempts: int
    expires_at: datetime
    callback_initiated_at: datetime | None
    connected_at: datetime | None
    cancelled_at: datetime | None
    original_call_id: str | None
    callback_call_id: str | None
    created_at: datetime
    updated_at: datetime


class CampOnCancelResponse(BaseModel):
    status: str
