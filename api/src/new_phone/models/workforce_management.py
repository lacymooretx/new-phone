import uuid
from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin

# ── Enums ──


class WfmTimeOffStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


class WfmDayOfWeek(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# ── Models ──


class WfmShift(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "wfm_shifts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_wfm_shifts_tenant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant = relationship("Tenant", lazy="joined")
    schedule_entries = relationship("WfmScheduleEntry", back_populates="shift")


class WfmScheduleEntry(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "wfm_schedule_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "extension_id", "date", name="uq_wfm_schedule_entries_tenant_ext_date"),
    )

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
        index=True,
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wfm_shifts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    extension = relationship("Extension", lazy="joined")
    shift = relationship("WfmShift", back_populates="schedule_entries", lazy="joined")


class WfmTimeOffRequest(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "wfm_time_off_requests"

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
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=WfmTimeOffStatus.PENDING)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    extension = relationship("Extension", lazy="joined")
    reviewed_by = relationship("User", lazy="joined")


class WfmForecastConfig(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "wfm_forecast_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "queue_id", name="uq_wfm_forecast_configs_tenant_queue"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_sla_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    target_sla_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    shrinkage_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    lookback_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    tenant = relationship("Tenant", lazy="joined")
    queue = relationship("Queue", lazy="joined")
