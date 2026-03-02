import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from new_phone.models.device import KeySection, KeyType


def _normalize_mac(mac: str) -> str:
    """Normalize MAC address to 12 lowercase hex chars."""
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "").lower().strip()
    if len(cleaned) != 12:
        raise ValueError("MAC address must be 12 hex characters")
    try:
        int(cleaned, 16)
    except ValueError:
        raise ValueError("MAC address must contain only hex characters") from None
    return cleaned


class DeviceCreate(BaseModel):
    mac_address: str = Field(..., min_length=12, max_length=17)
    phone_model_id: uuid.UUID
    extension_id: uuid.UUID | None = None
    name: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=200)
    notes: str | None = None
    provisioning_enabled: bool = True

    @field_validator("mac_address")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        return _normalize_mac(v)


class DeviceUpdate(BaseModel):
    mac_address: str | None = Field(None, min_length=12, max_length=17)
    phone_model_id: uuid.UUID | None = None
    extension_id: uuid.UUID | None = None
    name: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=200)
    notes: str | None = None
    provisioning_enabled: bool | None = None

    @field_validator("mac_address")
    @classmethod
    def validate_mac(cls, v: str | None) -> str | None:
        if v is not None:
            return _normalize_mac(v)
        return v


class DeviceKeyCreate(BaseModel):
    key_section: KeySection = KeySection.LINE_KEY
    key_index: int = Field(..., ge=1)
    key_type: KeyType = KeyType.NONE
    label: str | None = Field(None, max_length=50)
    value: str | None = Field(None, max_length=100)
    line: int = Field(1, ge=1, le=6)


class DeviceKeyBulkUpdate(BaseModel):
    """Bulk replace all keys for a device."""
    keys: list[DeviceKeyCreate]


class DeviceKeyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_id: uuid.UUID
    key_section: str
    key_index: int
    key_type: str
    label: str | None
    value: str | None
    line: int
    created_at: datetime
    updated_at: datetime


class DeviceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    mac_address: str
    phone_model_id: uuid.UUID
    extension_id: uuid.UUID | None
    name: str | None
    location: str | None
    notes: str | None
    last_provisioned_at: datetime | None
    last_config_hash: str | None
    provisioning_enabled: bool
    is_active: bool
    deactivated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Nested info
    phone_model_name: str | None = None
    phone_model_manufacturer: str | None = None
    extension_number: str | None = None

    @classmethod
    def from_device(cls, device) -> "DeviceResponse":
        data = {
            "id": device.id,
            "tenant_id": device.tenant_id,
            "mac_address": device.mac_address,
            "phone_model_id": device.phone_model_id,
            "extension_id": device.extension_id,
            "name": device.name,
            "location": device.location,
            "notes": device.notes,
            "last_provisioned_at": device.last_provisioned_at,
            "last_config_hash": device.last_config_hash,
            "provisioning_enabled": device.provisioning_enabled,
            "is_active": device.is_active,
            "deactivated_at": device.deactivated_at,
            "created_at": device.created_at,
            "updated_at": device.updated_at,
            "phone_model_name": device.phone_model.model_name if device.phone_model else None,
            "phone_model_manufacturer": device.phone_model.manufacturer if device.phone_model else None,
            "extension_number": device.extension.extension_number if device.extension else None,
        }
        return cls(**data)
