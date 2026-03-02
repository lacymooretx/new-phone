import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.outbound_route import OutboundCIDRouteMode


class OutboundRouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dial_pattern: str = Field(..., min_length=1, max_length=100)
    prepend_digits: str | None = Field(None, max_length=20)
    strip_digits: int = Field(0, ge=0, le=20)
    cid_mode: OutboundCIDRouteMode = OutboundCIDRouteMode.EXTENSION
    custom_cid: str | None = Field(None, max_length=40)
    priority: int = Field(100, ge=0, le=9999)
    enabled: bool = True
    trunk_ids: list[uuid.UUID] = Field(default_factory=list)


class OutboundRouteUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    dial_pattern: str | None = Field(None, min_length=1, max_length=100)
    prepend_digits: str | None = Field(None, max_length=20)
    strip_digits: int | None = Field(None, ge=0, le=20)
    cid_mode: OutboundCIDRouteMode | None = None
    custom_cid: str | None = Field(None, max_length=40)
    priority: int | None = Field(None, ge=0, le=9999)
    enabled: bool | None = None
    trunk_ids: list[uuid.UUID] | None = None


class OutboundRouteTrunkResponse(BaseModel):
    model_config = {"from_attributes": True}

    trunk_id: uuid.UUID
    position: int


class OutboundRouteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    dial_pattern: str
    prepend_digits: str | None
    strip_digits: int
    cid_mode: str
    custom_cid: str | None
    priority: int
    enabled: bool
    is_active: bool
    trunk_ids: list[uuid.UUID] = []
    created_at: datetime
    updated_at: datetime
