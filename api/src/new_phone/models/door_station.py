import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class DoorStation(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "door_stations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str | None] = mapped_column("model", String(100), nullable=True)
    unlock_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unlock_http_method: Mapped[str] = mapped_column(String(10), nullable=False, default="POST")
    unlock_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    unlock_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    unlock_dtmf_key: Mapped[str | None] = mapped_column(String(5), nullable=True)
    ring_dest_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ring_dest_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    extension = relationship("Extension", lazy="joined")
    site = relationship("Site", lazy="joined")
    access_logs = relationship(
        "DoorAccessLog",
        back_populates="door_station",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DoorAccessLog(Base):
    """Immutable audit log for door access events."""

    __tablename__ = "door_access_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    door_station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("door_stations.id", ondelete="CASCADE"),
        nullable=False,
    )
    caller_extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="SET NULL"),
        nullable=True,
    )
    answered_by_extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="SET NULL"),
        nullable=True,
    )
    door_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unlocked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cdr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_detail_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    call_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    call_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlock_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    door_station = relationship("DoorStation", back_populates="access_logs")
    caller_extension = relationship("Extension", foreign_keys=[caller_extension_id], lazy="joined")
    answered_by_extension = relationship(
        "Extension", foreign_keys=[answered_by_extension_id], lazy="joined"
    )
    unlocked_by_user = relationship("User", lazy="joined")
    cdr = relationship("CallDetailRecord", lazy="joined")
