import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sip_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_moh_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audio_prompts.id", ondelete="SET NULL"),
        nullable=True,
    )
    default_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Lifecycle & quotas
    lifecycle_state: Mapped[str] = mapped_column(String(20), nullable=False, default="trial")
    max_extensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_dids: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_concurrent_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    users = relationship("User", back_populates="tenant", lazy="selectin")
    default_moh_prompt = relationship("AudioPrompt", foreign_keys=[default_moh_prompt_id], lazy="joined")
    sso_provider = relationship("SSOProvider", back_populates="tenant", uselist=False, lazy="selectin")
