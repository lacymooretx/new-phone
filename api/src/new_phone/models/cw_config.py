import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class CWConfig(Base, TimestampMixin):
    __tablename__ = "cw_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    company_id: Mapped[str] = mapped_column(String(100), nullable=False)
    public_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    private_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, server_default="https://na.myconnectwise.net")
    api_version: Mapped[str] = mapped_column(String(20), nullable=False, server_default="2025.1")
    default_board_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_status_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_ticket_missed_calls: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    auto_ticket_voicemails: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    auto_ticket_completed_calls: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    min_call_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
    company_mappings = relationship("CWCompanyMapping", back_populates="cw_config", lazy="selectin", cascade="all, delete-orphan")
