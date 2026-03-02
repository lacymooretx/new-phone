import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PanicNotificationTargetCreate(BaseModel):
    target_type: str = Field(..., pattern="^(email|sms|page_group|webhook|user)$")
    target_value: str = Field(..., min_length=1, max_length=500)
    priority: int = Field(0, ge=0)
    is_active: bool = True


class PanicNotificationTargetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    security_config_id: uuid.UUID
    target_type: str
    target_value: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SecurityConfigUpdate(BaseModel):
    panic_enabled: bool | None = None
    silent_intercom_enabled: bool | None = None
    panic_feature_code: str | None = Field(None, max_length=20)
    emergency_allcall_code: str | None = Field(None, max_length=20)
    silent_intercom_max_seconds: int | None = Field(None, ge=30, le=3600)
    auto_dial_911: bool | None = None
    is_active: bool | None = None


class SecurityConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    panic_enabled: bool
    silent_intercom_enabled: bool
    panic_feature_code: str
    emergency_allcall_code: str
    silent_intercom_max_seconds: int
    auto_dial_911: bool
    is_active: bool
    notification_targets: list[PanicNotificationTargetResponse] = []
    created_at: datetime
    updated_at: datetime
