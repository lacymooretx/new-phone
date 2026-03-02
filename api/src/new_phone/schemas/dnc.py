import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field

# ── Paginated Response ──


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int


# ── DNC List ──


class DNCListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    list_type: str = Field("internal", max_length=20)
    source_url: str | None = Field(None, max_length=500)


class DNCListUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    list_type: str | None = Field(None, max_length=20)
    source_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class DNCListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    list_type: str
    source_url: str | None
    last_refreshed_at: datetime | None
    is_active: bool
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime


# ── DNC Entry ──


class DNCEntryCreate(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=20)
    reason: str | None = None
    source: str = Field("manual", max_length=20)
    expires_at: datetime | None = None


class DNCEntryBulkCreate(BaseModel):
    phone_numbers: list[str] = Field(..., min_length=1, max_length=10000)
    reason: str | None = None
    source: str = Field("bulk_upload", max_length=20)


class DNCEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    dnc_list_id: uuid.UUID
    phone_number: str
    added_by_user_id: uuid.UUID | None
    reason: str | None
    source: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BulkUploadResult(BaseModel):
    added: int
    skipped: int
    total: int


# ── DNC Check ──


class DNCCheckRequest(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=20)


class DNCCheckResult(BaseModel):
    is_blocked: bool
    matched_lists: list[str]
    has_consent: bool
    calling_window_ok: bool
    details: dict | None = None


# ── Consent Record ──


class ConsentRecordCreate(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=20)
    campaign_type: str = Field(..., max_length=20)
    consent_method: str = Field(..., max_length=20)
    consent_text: str | None = None
    consented_at: datetime | None = None
    metadata: dict | None = None


class ConsentRecordResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    phone_number: str
    campaign_type: str
    consent_method: str
    consent_text: str | None
    consented_at: datetime
    revoked_at: datetime | None
    is_active: bool
    metadata_json: dict | None = Field(None, alias="metadata_json")
    recorded_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ── Compliance Settings ──


class ComplianceSettingsUpdate(BaseModel):
    calling_window_start: time | None = None
    calling_window_end: time | None = None
    default_timezone: str | None = Field(None, max_length=50)
    enforce_calling_window: bool | None = None
    sync_sms_optout_to_dnc: bool | None = None
    auto_dnc_on_request: bool | None = None
    national_dnc_enabled: bool | None = None


class ComplianceSettingsResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    calling_window_start: time
    calling_window_end: time
    default_timezone: str
    enforce_calling_window: bool
    sync_sms_optout_to_dnc: bool
    auto_dnc_on_request: bool
    national_dnc_enabled: bool
    created_at: datetime
    updated_at: datetime


# ── Compliance Audit Log ──


class ComplianceAuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: str
    phone_number: str | None
    user_id: uuid.UUID | None
    details: dict | None
    created_at: datetime
