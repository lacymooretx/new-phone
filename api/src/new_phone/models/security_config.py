import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class SecurityConfig(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "security_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    panic_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    silent_intercom_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    panic_feature_code: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="*0911"
    )
    emergency_allcall_code: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="*0999"
    )
    silent_intercom_max_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="300"
    )
    auto_dial_911: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    notification_targets = relationship(
        "PanicNotificationTarget",
        back_populates="security_config",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PanicNotificationTarget(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "panic_notification_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    security_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # email/sms/page_group/webhook/user
    target_value: Mapped[str] = mapped_column(String(500), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    security_config = relationship("SecurityConfig", back_populates="notification_targets")
