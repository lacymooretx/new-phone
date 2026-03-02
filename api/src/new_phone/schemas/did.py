import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.did import DIDProvider, DIDStatus


class DIDCreate(BaseModel):
    number: str = Field(..., min_length=1, max_length=20, pattern=r"^\+\d{1,19}$")
    provider: DIDProvider
    provider_sid: str | None = Field(None, max_length=255)
    status: DIDStatus = DIDStatus.ACTIVE
    is_emergency: bool = False
    sms_enabled: bool = False
    sms_queue_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None


class DIDUpdate(BaseModel):
    number: str | None = Field(None, min_length=1, max_length=20, pattern=r"^\+\d{1,19}$")
    provider: DIDProvider | None = None
    provider_sid: str | None = Field(None, max_length=255)
    status: DIDStatus | None = None
    is_emergency: bool | None = None
    sms_enabled: bool | None = None
    sms_queue_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None


class DIDResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    number: str
    provider: str
    provider_sid: str | None
    status: str
    is_emergency: bool
    sms_enabled: bool
    sms_queue_id: uuid.UUID | None
    site_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
