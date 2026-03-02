import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class PhoneAppConfig(Base, TenantScopedMixin, TimestampMixin):
    """Per-tenant configuration for desk phone XML apps."""

    __tablename__ = "phone_app_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # App toggles
    directory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    voicemail_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    call_history_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    queue_dashboard_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Display settings
    page_size: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    tenant = relationship("Tenant", lazy="joined")
