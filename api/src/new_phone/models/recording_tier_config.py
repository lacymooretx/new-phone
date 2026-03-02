import uuid

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class RecordingTierConfig(Base, TimestampMixin):
    __tablename__ = "recording_tier_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    hot_tier_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="90")
    cold_tier_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="365"
    )
    retrieval_cache_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")
    auto_tier_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    auto_delete_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
