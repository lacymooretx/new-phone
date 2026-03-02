import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class TriggerSource(StrEnum):
    WEB = "web"
    MOBILE = "mobile"
    DESK_PHONE = "desk_phone"
    BUILDING_WEBHOOK = "building_webhook"


class AlertType(StrEnum):
    SILENT = "silent"
    AUDIBLE = "audible"


class AlertStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"


class PanicAlert(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "panic_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    triggered_from_extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False, default=AlertType.AUDIBLE)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AlertStatus.ACTIVE)
    location_building: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_floor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auto_911_dialed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    triggered_by_user = relationship("User", foreign_keys=[triggered_by_user_id], lazy="joined")
    triggered_from_extension = relationship("Extension", lazy="joined")
    acknowledged_by_user = relationship(
        "User", foreign_keys=[acknowledged_by_user_id], lazy="joined"
    )
    resolved_by_user = relationship("User", foreign_keys=[resolved_by_user_id], lazy="joined")
