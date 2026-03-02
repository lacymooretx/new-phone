import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.sip_trunk import InboundCIDMode, TrunkAuthType, TrunkTransport


class SIPTrunkCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    auth_type: TrunkAuthType
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(5061, ge=1, le=65535)

    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=255)
    ip_acl: str | None = None

    codec_preferences: dict | None = None
    max_channels: int = Field(30, ge=1, le=9999)
    transport: TrunkTransport = TrunkTransport.TLS
    inbound_cid_mode: InboundCIDMode = InboundCIDMode.PASSTHROUGH
    failover_trunk_id: uuid.UUID | None = None
    notes: str | None = None


class SIPTrunkUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    auth_type: TrunkAuthType | None = None
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)

    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=255)
    ip_acl: str | None = None

    codec_preferences: dict | None = None
    max_channels: int | None = Field(None, ge=1, le=9999)
    transport: TrunkTransport | None = None
    inbound_cid_mode: InboundCIDMode | None = None
    failover_trunk_id: uuid.UUID | None = None
    notes: str | None = None


class SIPTrunkResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    auth_type: str
    host: str
    port: int
    username: str | None
    ip_acl: str | None
    codec_preferences: dict | None
    max_channels: int
    transport: str
    inbound_cid_mode: str
    failover_trunk_id: uuid.UUID | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # NOTE: encrypted_password is NEVER returned
