import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.user import UserRole


class UserCreate(BaseModel):
    email: str = Field(..., max_length=320)
    password: str | None = Field(None, min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.TENANT_USER
    language: str = Field("en", max_length=10)


class UserUpdate(BaseModel):
    email: str | None = Field(None, max_length=320)
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None
    language: str | None = Field(None, max_length=10)


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    mfa_enabled: bool
    language: str
    auth_method: str
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
