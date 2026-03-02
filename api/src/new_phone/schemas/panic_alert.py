import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from new_phone.models.panic_alert import AlertType, TriggerSource


class PanicAlertTriggerRequest(BaseModel):
    alert_type: AlertType = AlertType.AUDIBLE
    trigger_source: TriggerSource = TriggerSource.WEB
    extension_id: uuid.UUID | None = None
    location_building: str | None = Field(None, max_length=255)
    location_floor: str | None = Field(None, max_length=100)
    location_description: str | None = Field(None, max_length=500)


class PanicAlertAcknowledgeRequest(BaseModel):
    pass  # user is extracted from auth


class PanicAlertResolveRequest(BaseModel):
    resolution_notes: str | None = Field(None, max_length=2000)
    mark_false_alarm: bool = False


class PanicAlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    triggered_by_user_id: uuid.UUID | None
    triggered_from_extension_id: uuid.UUID | None
    trigger_source: str
    alert_type: str
    status: str
    location_building: str | None
    location_floor: str | None
    location_description: str | None
    auto_911_dialed: bool
    acknowledged_by_user_id: uuid.UUID | None
    acknowledged_at: datetime | None
    resolved_by_user_id: uuid.UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime
