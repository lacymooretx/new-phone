import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.ring_group import RingStrategy


class RingGroupCreate(BaseModel):
    group_number: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    ring_strategy: RingStrategy = RingStrategy.SIMULTANEOUS
    ring_time: int = Field(25, ge=5, le=300)
    ring_time_per_member: int = Field(15, ge=5, le=120)
    skip_busy: bool = True
    cid_passthrough: bool = True
    confirm_calls: bool = False
    failover_dest_type: str | None = Field(None, max_length=20)
    failover_dest_id: uuid.UUID | None = None
    moh_prompt_id: uuid.UUID | None = None
    member_extension_ids: list[uuid.UUID] = Field(default_factory=list)


class RingGroupUpdate(BaseModel):
    group_number: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=255)
    ring_strategy: RingStrategy | None = None
    ring_time: int | None = Field(None, ge=5, le=300)
    ring_time_per_member: int | None = Field(None, ge=5, le=120)
    skip_busy: bool | None = None
    cid_passthrough: bool | None = None
    confirm_calls: bool | None = None
    failover_dest_type: str | None = Field(None, max_length=20)
    failover_dest_id: uuid.UUID | None = None
    moh_prompt_id: uuid.UUID | None = None
    member_extension_ids: list[uuid.UUID] | None = None


class RingGroupMemberResponse(BaseModel):
    model_config = {"from_attributes": True}

    extension_id: uuid.UUID
    position: int


class RingGroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    group_number: str
    name: str
    ring_strategy: str
    ring_time: int
    ring_time_per_member: int
    skip_busy: bool
    cid_passthrough: bool
    confirm_calls: bool
    failover_dest_type: str | None
    failover_dest_id: uuid.UUID | None
    moh_prompt_id: uuid.UUID | None = None
    member_extension_ids: list[uuid.UUID] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
