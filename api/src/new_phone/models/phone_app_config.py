import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class PhoneAppConfig(Base, TenantScopedMixin, TimestampMixin):
    """Per-tenant configuration for desk phone XML apps and provisioning."""

    __tablename__ = "phone_app_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # App toggles
    directory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    voicemail_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    call_history_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    queue_dashboard_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Display settings
    page_size: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Phone locale / display
    timezone: Mapped[str] = mapped_column(String(50), default="America/Chicago", nullable=False)
    language: Mapped[str] = mapped_column(String(30), default="English", nullable=False)
    date_format: Mapped[str] = mapped_column(String(5), default="2", nullable=False)
    time_format: Mapped[str] = mapped_column(String(5), default="1", nullable=False)

    # Security
    encrypted_phone_admin_password: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ringtone: Mapped[str] = mapped_column(String(50), default="Ring1.wav", nullable=False)
    backlight_time: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    screensaver_type: Mapped[str] = mapped_column(String(5), default="2", nullable=False)

    # Firmware
    firmware_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Codecs
    codec_priority: Mapped[str] = mapped_column(
        String(200), default="PCMU,PCMA,G722,G729,opus", nullable=False
    )

    # Feature codes
    pickup_code: Mapped[str] = mapped_column(String(10), default="*8", nullable=False)
    intercom_code: Mapped[str] = mapped_column(String(10), default="*80", nullable=False)
    parking_code: Mapped[str] = mapped_column(String(10), default="*85", nullable=False)
    dnd_on_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dnd_off_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fwd_unconditional_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fwd_busy_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fwd_noanswer_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Network / QoS
    dscp_sip: Mapped[int] = mapped_column(Integer, default=46, nullable=False)
    dscp_rtp: Mapped[int] = mapped_column(Integer, default=46, nullable=False)
    vlan_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vlan_priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Action URLs
    action_urls_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", lazy="joined")
