import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.extension import ClassOfService, OutboundCIDMode


class ExtensionCreate(BaseModel):
    extension_number: str = Field(..., min_length=1, max_length=20)
    user_id: uuid.UUID | None = None
    voicemail_box_id: uuid.UUID | None = None

    internal_cid_name: str | None = Field(None, max_length=100)
    internal_cid_number: str | None = Field(None, max_length=20)
    external_cid_name: str | None = Field(None, max_length=100)
    external_cid_number: str | None = Field(None, max_length=20)
    emergency_cid_number: str | None = Field(None, max_length=20)

    e911_street: str | None = Field(None, max_length=255)
    e911_city: str | None = Field(None, max_length=100)
    e911_state: str | None = Field(None, max_length=50)
    e911_zip: str | None = Field(None, max_length=20)
    e911_country: str | None = Field("US", max_length=2)

    call_forward_unconditional: str | None = Field(None, max_length=40)
    call_forward_busy: str | None = Field(None, max_length=40)
    call_forward_no_answer: str | None = Field(None, max_length=40)
    call_forward_not_registered: str | None = Field(None, max_length=40)
    call_forward_ring_time: int = Field(25, ge=5, le=120)

    dnd_enabled: bool = False
    call_waiting: bool = True
    max_registrations: int = Field(3, ge=1, le=10)
    outbound_cid_mode: OutboundCIDMode = OutboundCIDMode.INTERNAL
    class_of_service: ClassOfService = ClassOfService.DOMESTIC
    recording_policy: str = Field("never", pattern="^(never|always|on_demand)$")
    notes: str | None = None
    pickup_group: str | None = Field(None, max_length=20)
    site_id: uuid.UUID | None = None


class ExtensionUpdate(BaseModel):
    extension_number: str | None = Field(None, min_length=1, max_length=20)
    user_id: uuid.UUID | None = None
    voicemail_box_id: uuid.UUID | None = None

    internal_cid_name: str | None = Field(None, max_length=100)
    internal_cid_number: str | None = Field(None, max_length=20)
    external_cid_name: str | None = Field(None, max_length=100)
    external_cid_number: str | None = Field(None, max_length=20)
    emergency_cid_number: str | None = Field(None, max_length=20)

    e911_street: str | None = Field(None, max_length=255)
    e911_city: str | None = Field(None, max_length=100)
    e911_state: str | None = Field(None, max_length=50)
    e911_zip: str | None = Field(None, max_length=20)
    e911_country: str | None = Field(None, max_length=2)

    call_forward_unconditional: str | None = Field(None, max_length=40)
    call_forward_busy: str | None = Field(None, max_length=40)
    call_forward_no_answer: str | None = Field(None, max_length=40)
    call_forward_not_registered: str | None = Field(None, max_length=40)
    call_forward_ring_time: int | None = Field(None, ge=5, le=120)

    dnd_enabled: bool | None = None
    call_waiting: bool | None = None
    max_registrations: int | None = Field(None, ge=1, le=10)
    outbound_cid_mode: OutboundCIDMode | None = None
    class_of_service: ClassOfService | None = None
    recording_policy: str | None = Field(None, pattern="^(never|always|on_demand)$")
    notes: str | None = None
    pickup_group: str | None = Field(None, max_length=20)
    site_id: uuid.UUID | None = None


class ExtensionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    extension_number: str
    sip_username: str
    user_id: uuid.UUID | None
    voicemail_box_id: uuid.UUID | None

    internal_cid_name: str | None
    internal_cid_number: str | None
    external_cid_name: str | None
    external_cid_number: str | None
    emergency_cid_number: str | None

    e911_street: str | None
    e911_city: str | None
    e911_state: str | None
    e911_zip: str | None
    e911_country: str | None

    call_forward_unconditional: str | None
    call_forward_busy: str | None
    call_forward_no_answer: str | None
    call_forward_not_registered: str | None
    call_forward_ring_time: int

    dnd_enabled: bool
    call_waiting: bool
    max_registrations: int
    outbound_cid_mode: str
    class_of_service: str
    recording_policy: str
    notes: str | None
    agent_status: str | None = None
    pickup_group: str | None = None
    site_id: uuid.UUID | None = None

    is_active: bool
    created_at: datetime
    updated_at: datetime


class SIPPasswordResetResponse(BaseModel):
    sip_password: str
