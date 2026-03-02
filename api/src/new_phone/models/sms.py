import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class SMSProvider(StrEnum):
    CLEARLYIP = "clearlyip"
    TWILIO = "twilio"


class ConversationState(StrEnum):
    OPEN = "open"
    WAITING = "waiting"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RECEIVED = "received"


class OptOutReason(StrEnum):
    KEYWORD_STOP = "keyword_stop"
    MANUAL = "manual"
    API = "api"


class SMSProviderConfig(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "sms_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", lazy="joined")


class Conversation(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "did_id", "remote_number", name="uq_conversation_tenant_did_remote"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    did_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    remote_number: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="sms")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default=ConversationState.OPEN)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    queue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    did = relationship("DID", lazy="joined")
    assigned_to_user = relationship("User", lazy="joined")
    queue = relationship("Queue", lazy="joined")
    messages = relationship("Message", back_populates="conversation", lazy="selectin", order_by="Message.created_at")
    notes = relationship("ConversationNote", back_populates="conversation", lazy="selectin", order_by="ConversationNote.created_at")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MessageStatus.QUEUED)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    conversation = relationship("Conversation", back_populates="messages")
    sent_by_user = relationship("User", lazy="joined")


class ConversationNote(Base, TimestampMixin):
    __tablename__ = "conversation_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    conversation = relationship("Conversation", back_populates="notes")
    user = relationship("User", lazy="joined")


class SMSOptOut(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "sms_opt_outs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "did_id", "phone_number", name="uq_opt_out_tenant_did_phone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    did_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dids.id", ondelete="CASCADE"),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    opted_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opted_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_opted_out: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
