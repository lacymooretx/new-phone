import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class PhoneAppConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID

    # App toggles
    directory_enabled: bool
    voicemail_enabled: bool
    call_history_enabled: bool
    parking_enabled: bool
    queue_dashboard_enabled: bool
    settings_enabled: bool
    page_size: int
    company_name: str | None

    # Phone locale / display
    timezone: str
    language: str
    date_format: str
    time_format: str

    # Security — expose bool flag, never the ciphertext
    has_phone_admin_password: bool = False

    # Branding
    logo_url: str | None
    ringtone: str
    backlight_time: int
    screensaver_type: str

    # Firmware
    firmware_url: str | None

    # Codecs
    codec_priority: str

    # Feature codes
    pickup_code: str
    intercom_code: str
    parking_code: str
    dnd_on_code: str | None
    dnd_off_code: str | None
    fwd_unconditional_code: str | None
    fwd_busy_code: str | None
    fwd_noanswer_code: str | None

    # Network / QoS
    dscp_sip: int
    dscp_rtp: int
    vlan_enabled: bool
    vlan_id: int | None
    vlan_priority: int

    # Action URLs
    action_urls_enabled: bool

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="wrap")
    @classmethod
    def _compute_has_pw(cls, values: object, handler: object) -> "PhoneAppConfigResponse":
        # Extract encrypted_phone_admin_password from ORM object before validation
        has_pw = False
        if hasattr(values, "encrypted_phone_admin_password"):
            has_pw = bool(values.encrypted_phone_admin_password)
        result = handler(values)  # type: ignore[operator]
        result.has_phone_admin_password = has_pw
        return result


class PhoneAppConfigUpdate(BaseModel):
    # App toggles
    directory_enabled: bool | None = None
    voicemail_enabled: bool | None = None
    call_history_enabled: bool | None = None
    parking_enabled: bool | None = None
    queue_dashboard_enabled: bool | None = None
    settings_enabled: bool | None = None
    page_size: int | None = Field(None, ge=5, le=50)
    company_name: str | None = None

    # Phone locale / display
    timezone: str | None = None
    language: str | None = None
    date_format: str | None = None
    time_format: str | None = None

    # Security — accept plaintext, service encrypts before storing
    phone_admin_password: str | None = None

    # Branding
    logo_url: str | None = None
    ringtone: str | None = None
    backlight_time: int | None = Field(None, ge=0, le=1800)
    screensaver_type: str | None = None

    # Firmware
    firmware_url: str | None = None

    # Codecs
    codec_priority: str | None = None

    # Feature codes
    pickup_code: str | None = None
    intercom_code: str | None = None
    parking_code: str | None = None
    dnd_on_code: str | None = None
    dnd_off_code: str | None = None
    fwd_unconditional_code: str | None = None
    fwd_busy_code: str | None = None
    fwd_noanswer_code: str | None = None

    # Network / QoS
    dscp_sip: int | None = Field(None, ge=0, le=63)
    dscp_rtp: int | None = Field(None, ge=0, le=63)
    vlan_enabled: bool | None = None
    vlan_id: int | None = Field(None, ge=1, le=4094)
    vlan_priority: int | None = Field(None, ge=0, le=7)

    # Action URLs
    action_urls_enabled: bool | None = None
