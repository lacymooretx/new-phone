import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class UsageMetric(StrEnum):
    CALL_MINUTES = "call_minutes"
    SMS_MESSAGES = "sms_messages"
    RECORDING_STORAGE_GB = "recording_storage_gb"
    ACTIVE_EXTENSIONS = "active_extensions"
    ACTIVE_DIDS = "active_dids"
    API_CALLS = "api_calls"


class UsageRecord(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)


class RateDeck(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "rate_decks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    entries = relationship("RateDeckEntry", back_populates="rate_deck", lazy="selectin", cascade="all, delete-orphan")


class RateDeckEntry(Base, TimestampMixin):
    __tablename__ = "rate_deck_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rate_deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rate_decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    per_minute_rate: Mapped[float] = mapped_column(Float, nullable=False)
    connection_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minimum_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rate_deck = relationship("RateDeck", back_populates="entries")

    __table_args__ = (
        UniqueConstraint("rate_deck_id", "prefix", name="uq_rate_deck_prefix"),
    )


class BillingConfig(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "billing_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    billing_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    connectwise_agreement_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pax8_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_cycle_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auto_generate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
