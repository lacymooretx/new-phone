import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TenantScopedMixin, TimestampMixin


class UserRole(StrEnum):
    MSP_SUPER_ADMIN = "msp_super_admin"
    MSP_TECH = "msp_tech"
    TENANT_ADMIN = "tenant_admin"
    TENANT_MANAGER = "tenant_manager"
    TENANT_USER = "tenant_user"


class User(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default=UserRole.TENANT_USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Auth tracking
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Refresh tokens
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    auth_method: Mapped[str] = mapped_column(String(20), nullable=False, default="local")

    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="users", lazy="joined")
    sso_links = relationship(
        "UserSSOLink",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
