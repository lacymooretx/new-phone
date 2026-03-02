import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class OutboundCIDMode(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    CUSTOM = "custom"


class ClassOfService(StrEnum):
    INTERNATIONAL = "international"
    DOMESTIC = "domestic"
    LOCAL = "local"
    INTERNAL = "internal"
    EMERGENCY_ONLY = "emergency_only"


class Extension(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "extensions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extension_number: Mapped[str] = mapped_column(String(20), nullable=False)
    # SIP credentials
    sip_username: Mapped[str] = mapped_column(String(100), nullable=False)
    sip_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_sip_password: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Assigned user (optional)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Voicemail box (optional)
    voicemail_box_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voicemail_boxes.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    # Caller ID
    internal_cid_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    internal_cid_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    external_cid_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_cid_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emergency_cid_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # E911
    e911_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    e911_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    e911_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    e911_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    e911_country: Mapped[str | None] = mapped_column(String(2), nullable=True, default="US")

    # Call forwarding (JSONB stores rules for each type)
    call_forward_unconditional: Mapped[str | None] = mapped_column(String(40), nullable=True)
    call_forward_busy: Mapped[str | None] = mapped_column(String(40), nullable=True)
    call_forward_no_answer: Mapped[str | None] = mapped_column(String(40), nullable=True)
    call_forward_not_registered: Mapped[str | None] = mapped_column(String(40), nullable=True)
    call_forward_ring_time: Mapped[int] = mapped_column(Integer, default=25, nullable=False)

    # Features
    dnd_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    call_waiting: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_registrations: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    outbound_cid_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OutboundCIDMode.INTERNAL
    )
    class_of_service: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ClassOfService.DOMESTIC
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Call recording policy: never / always / on_demand
    recording_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="never")

    # Queue agent status (null = not a queue agent)
    agent_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Call pickup group (extensions in same group can pick up each other's calls)
    pickup_group: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    user = relationship("User", lazy="joined")
    voicemail_box = relationship("VoicemailBox", back_populates="extensions", lazy="joined")
    site = relationship("Site", lazy="joined")
