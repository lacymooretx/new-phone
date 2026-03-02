import uuid
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class PromptCategory(StrEnum):
    GENERAL = "general"
    IVR_GREETING = "ivr_greeting"
    VOICEMAIL_GREETING = "voicemail_greeting"
    MOH = "moh"
    ANNOUNCEMENT = "announcement"


class AudioPrompt(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "audio_prompts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default=PromptCategory.GENERAL)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="wav")
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=8000)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", foreign_keys=[tenant_id], lazy="joined")
    site = relationship("Site", foreign_keys=[site_id], lazy="joined")
