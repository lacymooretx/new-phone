import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.inbound_route import InboundDestType


class InboundRouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    did_id: uuid.UUID | None = None
    destination_type: InboundDestType
    destination_id: uuid.UUID | None = None
    cid_name_prefix: str | None = Field(None, max_length=50)
    time_conditions: dict | None = None
    enabled: bool = True


class InboundRouteUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    did_id: uuid.UUID | None = None
    destination_type: InboundDestType | None = None
    destination_id: uuid.UUID | None = None
    cid_name_prefix: str | None = Field(None, max_length=50)
    time_conditions: dict | None = None
    enabled: bool | None = None


class InboundRouteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    did_id: uuid.UUID | None
    destination_type: str
    destination_id: uuid.UUID | None
    cid_name_prefix: str | None
    time_conditions: dict | None
    enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
