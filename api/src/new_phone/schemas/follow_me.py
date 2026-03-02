import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.follow_me import FollowMeStrategy


class FollowMeDestinationData(BaseModel):
    destination: str = Field(..., min_length=1, max_length=40)
    ring_time: int = Field(20, ge=5, le=120)


class FollowMeUpdate(BaseModel):
    enabled: bool = False
    strategy: FollowMeStrategy = FollowMeStrategy.SEQUENTIAL
    ring_extension_first: bool = True
    extension_ring_time: int = Field(25, ge=5, le=120)
    destinations: list[FollowMeDestinationData] = Field(default_factory=list, max_length=10)


class FollowMeDestinationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    position: int
    destination: str
    ring_time: int


class FollowMeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    extension_id: uuid.UUID
    enabled: bool
    strategy: str
    ring_extension_first: bool
    extension_ring_time: int
    destinations: list[FollowMeDestinationResponse] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
