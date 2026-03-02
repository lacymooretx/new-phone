import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.page_group import PageMode


class PageGroupMemberCreate(BaseModel):
    extension_id: uuid.UUID
    position: int = Field(0, ge=0, le=100)


class PageGroupMemberResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    page_group_id: uuid.UUID
    extension_id: uuid.UUID
    position: int


class PageGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    page_number: str = Field(..., min_length=1, max_length=20)
    description: str | None = None
    page_mode: PageMode = PageMode.ONE_WAY
    timeout: int = Field(60, ge=1, le=300)
    members: list[PageGroupMemberCreate] = Field(default_factory=list)
    site_id: uuid.UUID | None = None


class PageGroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    page_number: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = None
    page_mode: PageMode | None = None
    timeout: int | None = Field(None, ge=1, le=300)
    members: list[PageGroupMemberCreate] | None = None
    site_id: uuid.UUID | None = None


class PageGroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    page_number: str
    description: str | None
    page_mode: str
    timeout: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    site_id: uuid.UUID | None = None
    members: list[PageGroupMemberResponse] = []
