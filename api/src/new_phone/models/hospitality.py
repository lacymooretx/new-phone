import uuid
from datetime import datetime, time
from enum import StrEnum

from sqlalchemy import (
    Boolean,
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


class RoomStatus(StrEnum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    CHECKOUT = "checkout"
    MAINTENANCE = "maintenance"


class HousekeepingStatus(StrEnum):
    CLEAN = "clean"
    DIRTY = "dirty"
    INSPECTED = "inspected"
    OUT_OF_ORDER = "out_of_order"


class Room(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "room_number", name="uq_rooms_tenant_room_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="SET NULL"),
        nullable=True,
    )
    floor: Mapped[str | None] = mapped_column(String(10), nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RoomStatus.VACANT)
    housekeeping_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=HousekeepingStatus.CLEAN
    )
    guest_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    guest_checkout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wake_up_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    wake_up_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    restricted_dialing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    extension = relationship("Extension", foreign_keys=[extension_id], lazy="joined")
    wake_up_calls = relationship("WakeUpCall", back_populates="room", lazy="selectin")


class WakeUpCall(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "wake_up_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    room = relationship("Room", back_populates="wake_up_calls", lazy="joined")
