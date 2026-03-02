import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class KeySection(StrEnum):
    LINE_KEY = "line_key"
    EXPANSION_1 = "expansion_1"
    EXPANSION_2 = "expansion_2"
    EXPANSION_3 = "expansion_3"


class KeyType(StrEnum):
    LINE = "line"
    BLF = "blf"
    SPEED_DIAL = "speed_dial"
    DTMF = "dtmf"
    PARK = "park"
    INTERCOM = "intercom"
    NONE = "none"


class Device(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mac_address: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    phone_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phone_models.id", ondelete="RESTRICT"),
        nullable=False,
    )
    extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provisioning_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    phone_model = relationship("PhoneModel", lazy="joined")
    extension = relationship("Extension", lazy="joined")
    keys = relationship("DeviceKey", back_populates="device", cascade="all, delete-orphan", lazy="selectin")


class DeviceKey(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "device_keys"
    __table_args__ = (
        UniqueConstraint("device_id", "key_section", "key_index", name="uq_device_key_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_section: Mapped[str] = mapped_column(String(20), nullable=False)
    key_index: Mapped[int] = mapped_column(Integer, nullable=False)
    key_type: Mapped[str] = mapped_column(String(20), nullable=False, default=KeyType.NONE)
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    line: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    device = relationship("Device", back_populates="keys")
