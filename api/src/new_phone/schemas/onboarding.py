"""Pydantic schemas for tenant onboarding."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OnboardingRequest(BaseModel):
    """Full tenant onboarding request."""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant display name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
        description="URL-safe slug",
    )
    domain: str | None = Field(None, max_length=255, description="Primary domain")
    admin_email: str = Field(..., max_length=320, description="Initial admin user email")
    admin_first_name: str = Field("Admin", max_length=100)
    admin_last_name: str = Field("User", max_length=100)
    plan: str = Field("trial", description="Subscription plan: trial, starter, professional, enterprise")

    # Optional provider overrides
    provider: str = Field("clearlyip", description="Telephony provider: clearlyip or twilio")
    region: str = Field("us-east", max_length=50, description="Trunk region")
    area_code: str | None = Field(None, max_length=10, description="Preferred area code for initial DID")
    initial_did_count: int = Field(1, ge=0, le=20, description="Number of DIDs to purchase")
    initial_extensions: int = Field(10, ge=0, le=1000, description="Number of default extensions")


class OnboardingStepStatus(BaseModel):
    """Status of a single onboarding step."""

    step: str
    status: str  # pending, in_progress, completed, failed
    detail: str | None = None


class OnboardingStatusResponse(BaseModel):
    """Current state of a tenant onboarding process."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    tenant_name: str
    lifecycle_state: str
    steps: list[OnboardingStepStatus]
    completed: bool
    created_at: datetime | None = None


class OnboardingResponse(BaseModel):
    """Immediate response after kicking off onboarding."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    tenant_name: str
    slug: str
    lifecycle_state: str
    admin_email: str
    trunk_provisioned: bool
    dids_purchased: int
    extensions_created: int
    message: str
