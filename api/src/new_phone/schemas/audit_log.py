import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    changes: dict | None
    ip_address: str
    user_agent: str | None
    created_at: datetime


class AuditLogListParams(BaseModel):
    tenant_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    action: str | None = None
    resource_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=200)
