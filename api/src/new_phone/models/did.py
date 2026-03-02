import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class DIDProvider(StrEnum):
    CLEARLYIP = "clearlyip"
    TWILIO = "twilio"
    MANUAL = "manual"


class DIDStatus(StrEnum):
    ACTIVE = "active"
    PORTING = "porting"
    RESERVED = "reserved"
    RELEASED = "released"


class DID(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "dids"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_sid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DIDStatus.ACTIVE)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_queue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    sms_queue = relationship("Queue", lazy="joined")
    site = relationship("Site", lazy="joined")
