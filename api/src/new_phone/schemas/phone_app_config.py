import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PhoneAppConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    directory_enabled: bool
    voicemail_enabled: bool
    call_history_enabled: bool
    parking_enabled: bool
    queue_dashboard_enabled: bool
    settings_enabled: bool
    page_size: int
    company_name: str | None
    created_at: datetime
    updated_at: datetime


class PhoneAppConfigUpdate(BaseModel):
    directory_enabled: bool | None = None
    voicemail_enabled: bool | None = None
    call_history_enabled: bool | None = None
    parking_enabled: bool | None = None
    queue_dashboard_enabled: bool | None = None
    settings_enabled: bool | None = None
    page_size: int | None = Field(None, ge=5, le=50)
    company_name: str | None = None
