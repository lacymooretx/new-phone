import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Usage Records ─────────────────────────────────────────


class UsageRecordCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    metric: str = Field(min_length=1, max_length=50)
    quantity: float = Field(ge=0)
    unit_cost: float | None = None
    total_cost: float | None = None


class UsageRecordResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    metric: str
    quantity: float
    unit_cost: float | None
    total_cost: float | None
    created_at: datetime
    updated_at: datetime


# ── Rate Decks ────────────────────────────────────────────


class RateDeckCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    is_default: bool = False
    is_active: bool = True


class RateDeckUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class RateDeckResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Rate Deck Entries ─────────────────────────────────────


class RateDeckEntryCreate(BaseModel):
    prefix: str = Field(min_length=1, max_length=20)
    destination: str = Field(min_length=1, max_length=100)
    per_minute_rate: float = Field(ge=0)
    connection_fee: float = Field(ge=0, default=0.0)
    minimum_seconds: int = Field(ge=0, default=0)


class RateDeckEntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    rate_deck_id: uuid.UUID
    prefix: str
    destination: str
    per_minute_rate: float
    connection_fee: float
    minimum_seconds: int
    created_at: datetime
    updated_at: datetime


# ── Rate Lookup Result ────────────────────────────────────


class RateLookupResponse(BaseModel):
    dialed_number: str
    matched_prefix: str | None
    destination: str | None
    per_minute_rate: float | None
    connection_fee: float | None
    minimum_seconds: int | None


# ── Billing Config ────────────────────────────────────────


class BillingConfigUpdate(BaseModel):
    billing_provider: str | None = Field(None, pattern=r"^(connectwise|pax8|manual)$")
    connectwise_agreement_id: str | None = None
    pax8_subscription_id: str | None = None
    billing_cycle_day: int | None = Field(None, ge=1, le=28)
    auto_generate: bool | None = None


class BillingConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    billing_provider: str
    connectwise_agreement_id: str | None
    pax8_subscription_id: str | None
    billing_cycle_day: int
    auto_generate: bool
    created_at: datetime
    updated_at: datetime
