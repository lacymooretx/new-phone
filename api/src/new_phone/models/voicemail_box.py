import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class GreetingType(StrEnum):
    DEFAULT = "default"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"
    NAME = "name"
    CUSTOM = "custom"


class VoicemailBox(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "voicemail_boxes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mailbox_number: Mapped[str] = mapped_column(String(20), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_pin: Mapped[str | None] = mapped_column(Text, nullable=True)
    greeting_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GreetingType.DEFAULT
    )
    email_notification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    max_messages: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
    extensions = relationship("Extension", back_populates="voicemail_box", lazy="selectin")
