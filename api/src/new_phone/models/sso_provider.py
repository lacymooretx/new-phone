import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class SSOProviderType:
    MICROSOFT = "microsoft"
    GOOGLE = "google"


class SSOProvider(Base, TimestampMixin):
    __tablename__ = "sso_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    issuer_url: Mapped[str] = mapped_column(String(500), nullable=False)
    discovery_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scopes: Mapped[str] = mapped_column(String(500), nullable=False, default="openid email profile")
    auto_provision: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_role: Mapped[str] = mapped_column(String(30), nullable=False, default="tenant_user")
    enforce_sso: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", back_populates="sso_provider", lazy="joined")
    role_mappings = relationship(
        "SSORoleMapping",
        back_populates="sso_provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
