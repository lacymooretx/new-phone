import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class CampOnStatus(enum.StrEnum):
    pending = "pending"
    callback_initiated = "callback_initiated"
    connected = "connected"
    expired = "expired"
    cancelled = "cancelled"
    caller_unavailable = "caller_unavailable"


class CampOnReason(enum.StrEnum):
    busy = "busy"
    no_answer = "no_answer"


class CampOnConfig(Base, TimestampMixin):
    __tablename__ = "camp_on_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_code: Mapped[str] = mapped_column(String(20), nullable=False, server_default="*88")
    timeout_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    max_camp_ons_per_target: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="5"
    )
    callback_retry_delay_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="30"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")


class CampOnRequest(Base, TimestampMixin):
    __tablename__ = "camp_on_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    caller_extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_extension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    caller_extension_number: Mapped[str] = mapped_column(String(20), nullable=False)
    target_extension_number: Mapped[str] = mapped_column(String(20), nullable=False)
    caller_sip_username: Mapped[str] = mapped_column(String(100), nullable=False)
    target_sip_username: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    callback_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    callback_initiated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    original_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    callback_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    caller_extension = relationship("Extension", foreign_keys=[caller_extension_id], lazy="joined")
    target_extension = relationship("Extension", foreign_keys=[target_extension_id], lazy="joined")
