import uuid
from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class HolidayCalendar(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "holiday_calendars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    entries = relationship(
        "HolidayEntry",
        back_populates="calendar",
        order_by="HolidayEntry.date",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tenant = relationship("Tenant", lazy="joined")


class HolidayEntry(Base):
    __tablename__ = "holiday_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("holiday_calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    recur_annually: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    calendar = relationship("HolidayCalendar", back_populates="entries")
