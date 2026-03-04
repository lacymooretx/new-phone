import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.migration import MigrationStatus

# ---------------------------------------------------------------------------
# MigrationJob schemas
# ---------------------------------------------------------------------------


class MigrationJobCreate(BaseModel):
    source_platform: str = Field(
        ..., pattern=r"^(freepbx|threecx|csv)$", max_length=20
    )
    file_name: str = Field(..., min_length=1, max_length=255)
    file_content_base64: str = Field(
        ..., description="Base64-encoded file content"
    )


class MigrationJobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    source_platform: str
    status: MigrationStatus
    file_name: str
    total_records: int
    imported_records: int
    failed_records: int
    validation_errors: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# InterTenantRoute schemas
# ---------------------------------------------------------------------------


class InterTenantRouteCreate(BaseModel):
    source_tenant_id: uuid.UUID
    target_tenant_id: uuid.UUID
    prefix: str = Field(..., min_length=1, max_length=10, pattern=r"^\d+$")


class InterTenantRouteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    source_tenant_id: uuid.UUID
    target_tenant_id: uuid.UUID
    prefix: str
    is_active: bool
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
