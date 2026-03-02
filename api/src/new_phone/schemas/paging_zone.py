import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PagingZoneMemberCreate(BaseModel):
    extension_id: uuid.UUID
    position: int = 0


class PagingZoneMemberResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    paging_zone_id: uuid.UUID
    extension_id: uuid.UUID
    position: int


class PagingZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    zone_number: str = Field(..., min_length=1, max_length=20)
    description: str | None = None
    is_emergency: bool = False
    priority: int = Field(0, ge=0)
    site_id: uuid.UUID | None = None
    members: list[PagingZoneMemberCreate] = Field(default_factory=list)


class PagingZoneUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    zone_number: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = None
    is_emergency: bool | None = None
    priority: int | None = Field(None, ge=0)
    site_id: uuid.UUID | None = None
    is_active: bool | None = None
    members: list[PagingZoneMemberCreate] | None = None


class PagingZoneResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    zone_number: str
    description: str | None
    is_emergency: bool
    priority: int
    site_id: uuid.UUID | None
    is_active: bool
    members: list[PagingZoneMemberResponse] = []
    created_at: datetime
    updated_at: datetime
