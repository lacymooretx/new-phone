import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cdr_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("call_detail_records.id", ondelete="SET NULL"), nullable=True
    )
    call_id: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="wav")
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=8000)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recording_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="always")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Storage tiering
    storage_tier: Mapped[str] = mapped_column(String(10), nullable=False, server_default="hot")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archive_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    archive_storage_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retrieval_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieval_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    legal_hold_set_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    legal_hold_set_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant = relationship("Tenant", lazy="joined")
    cdr = relationship("CallDetailRecord", back_populates="recordings", lazy="joined")
