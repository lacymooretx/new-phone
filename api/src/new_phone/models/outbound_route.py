import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class OutboundCIDRouteMode(StrEnum):
    EXTENSION = "extension"
    TRUNK = "trunk"
    CUSTOM = "custom"


class OutboundRoute(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "outbound_routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dial_pattern: Mapped[str] = mapped_column(String(100), nullable=False)
    prepend_digits: Mapped[str | None] = mapped_column(String(20), nullable=True)
    strip_digits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cid_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OutboundCIDRouteMode.EXTENSION
    )
    custom_cid: Mapped[str | None] = mapped_column(String(40), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    trunk_assignments = relationship(
        "OutboundRouteTrunk",
        back_populates="outbound_route",
        order_by="OutboundRouteTrunk.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class OutboundRouteTrunk(Base):
    __tablename__ = "outbound_route_trunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbound_route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outbound_routes.id", ondelete="CASCADE"),
        nullable=False,
    )
    trunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sip_trunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    outbound_route = relationship("OutboundRoute", back_populates="trunk_assignments")
    trunk = relationship("SIPTrunk", lazy="joined")
