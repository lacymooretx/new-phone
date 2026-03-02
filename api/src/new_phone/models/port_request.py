import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class PortRequestStatus(StrEnum):
    SUBMITTED = "submitted"
    PENDING_LOA = "pending_loa"
    LOA_SUBMITTED = "loa_submitted"
    FOC_RECEIVED = "foc_received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PortRequestProvider(StrEnum):
    CLEARLYIP = "clearlyip"
    TWILIO = "twilio"


class PortRequest(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "port_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    numbers: Mapped[list] = mapped_column(JSONB, nullable=False)
    current_carrier: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=PortRequestStatus.SUBMITTED
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_port_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loa_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    foc_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    requested_port_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_port_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant = relationship("Tenant", lazy="joined")
    submitter = relationship("User", lazy="joined")
    history = relationship(
        "PortRequestHistory",
        back_populates="port_request",
        lazy="selectin",
        order_by="PortRequestHistory.created_at.desc()",
    )


class PortRequestHistory(Base, TimestampMixin):
    __tablename__ = "port_request_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    port_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("port_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    port_request = relationship("PortRequest", back_populates="history")
    user = relationship("User", lazy="joined")
