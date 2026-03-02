import uuid
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class VMFolder(StrEnum):
    NEW = "new"
    SAVED = "saved"
    DELETED = "deleted"


class VoicemailMessage(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "voicemail_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voicemail_box_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voicemail_boxes.id", ondelete="CASCADE"),
        nullable=False,
    )
    caller_number: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    caller_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="wav")
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    folder: Mapped[str] = mapped_column(String(20), nullable=False, default=VMFolder.NEW)
    call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", lazy="joined")
    voicemail_box = relationship("VoicemailBox", lazy="joined")
