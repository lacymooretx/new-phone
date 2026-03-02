import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Brand Types ─────────────────────────────────────────────────────────

BrandType = Literal["sole_proprietor", "small_business", "large_business"]
BrandStatus = Literal["draft", "pending", "approved", "rejected"]

CampaignUseCase = Literal[
    "marketing",
    "customer_care",
    "account_notifications",
    "delivery_notifications",
    "mixed",
    "two_factor_auth",
    "polling_voting",
    "public_service",
    "emergency",
    "charity",
]
CampaignStatus = Literal["draft", "pending", "approved", "rejected", "suspended"]

DocumentType = Literal["privacy_policy", "terms_of_service", "opt_in_form"]


# ── Brand Schemas ───────────────────────────────────────────────────────


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ein: str = Field(..., min_length=1, max_length=20)
    ein_issuing_country: str = Field(default="US", min_length=2, max_length=2)
    brand_type: BrandType
    vertical: str = Field(..., min_length=1, max_length=50)
    website: str | None = Field(None, max_length=500)


class BrandUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    ein: str | None = Field(None, min_length=1, max_length=20)
    ein_issuing_country: str | None = Field(None, min_length=2, max_length=2)
    brand_type: BrandType | None = None
    vertical: str | None = Field(None, min_length=1, max_length=50)
    website: str | None = Field(None, max_length=500)


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    ein: str
    ein_issuing_country: str
    brand_type: str
    vertical: str
    website: str | None
    status: str
    provider_brand_id: str | None
    rejection_reason: str | None
    submitted_at: datetime | None
    approved_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Campaign Schemas ────────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    brand_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    use_case: CampaignUseCase
    description: str = Field(..., min_length=1)
    sample_messages: list[str] = Field(..., min_length=1, max_length=5)
    message_flow: str = Field(..., min_length=1)
    help_message: str = Field(..., min_length=1, max_length=500)
    opt_out_message: str = Field(..., min_length=1, max_length=500)
    opt_in_keywords: str = Field(default="START", max_length=255)
    opt_out_keywords: str = Field(default="STOP", max_length=255)
    help_keywords: str = Field(default="HELP", max_length=255)
    number_pool: list[str] | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    use_case: CampaignUseCase | None = None
    description: str | None = Field(None, min_length=1)
    sample_messages: list[str] | None = Field(None, min_length=1, max_length=5)
    message_flow: str | None = Field(None, min_length=1)
    help_message: str | None = Field(None, min_length=1, max_length=500)
    opt_out_message: str | None = Field(None, min_length=1, max_length=500)
    opt_in_keywords: str | None = Field(None, max_length=255)
    opt_out_keywords: str | None = Field(None, max_length=255)
    help_keywords: str | None = Field(None, max_length=255)
    number_pool: list[str] | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    use_case: str
    description: str
    sample_messages: list[str] | None
    message_flow: str
    help_message: str
    opt_out_message: str
    opt_in_keywords: str
    opt_out_keywords: str
    help_keywords: str
    number_pool: list[str] | None
    status: str
    provider_campaign_id: str | None
    rejection_reason: str | None
    submitted_at: datetime | None
    approved_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Compliance Document Schemas ─────────────────────────────────────────


class ComplianceDocUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: uuid.UUID
    document_type: str
    file_path: str
    original_filename: str
    uploaded_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
