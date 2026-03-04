import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── STIR/SHAKEN Config ──


class StirShakenConfigCreate(BaseModel):
    is_enabled: bool = False
    certificate_pem: str | None = None
    private_key_pem: str | None = None
    certificate_url: str | None = Field(None, max_length=500)
    default_attestation: str = Field("A", max_length=1)
    verify_inbound: bool = True


class StirShakenConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    certificate_pem: str | None = None
    private_key_pem: str | None = None
    certificate_url: str | None = Field(None, max_length=500)
    default_attestation: str | None = Field(None, max_length=1)
    verify_inbound: bool | None = None


class StirShakenConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    is_enabled: bool
    certificate_url: str | None
    default_attestation: str
    verify_inbound: bool
    created_at: datetime
    updated_at: datetime


# ── Spam Filter ──


class SpamFilterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    min_attestation: str | None = Field(None, max_length=1)
    spam_score_threshold: int = Field(50, ge=0, le=100)
    action: str = Field("block", max_length=20)


class SpamFilterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None
    min_attestation: str | None = Field(None, max_length=1)
    spam_score_threshold: int | None = Field(None, ge=0, le=100)
    action: str | None = Field(None, max_length=20)


class SpamFilterResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_active: bool
    min_attestation: str | None
    spam_score_threshold: int
    action: str
    created_at: datetime
    updated_at: datetime


# ── Spam Block List ──


class SpamBlockListCreate(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=20)
    reason: str | None = None
    blocked_at: datetime | None = None


class SpamBlockListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    phone_number: str
    reason: str | None
    blocked_at: datetime
    created_at: datetime
    updated_at: datetime


# ── Spam Allow List ──


class SpamAllowListCreate(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=20)
    label: str | None = Field(None, max_length=255)


class SpamAllowListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    phone_number: str
    label: str | None
    created_at: datetime
    updated_at: datetime


# ── Number Check ──


class NumberCheckRequest(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=20)


class NumberCheckResult(BaseModel):
    is_blocked: bool
    is_allowed: bool
    spam_score: int | None = None
