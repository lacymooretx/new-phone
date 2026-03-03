import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class TelephonyProviderConfig(Base, TimestampMixin):
    """Two-tier telephony provider credential store.

    Rows with ``tenant_id IS NULL`` are MSP-level platform defaults.
    Rows with a ``tenant_id`` are per-tenant overrides.

    Resolution order: tenant config -> MSP default -> env var fallback.
    """

    __tablename__ = "telephony_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", lazy="joined")

    __table_args__ = (
        # One active MSP default per provider type
        Index(
            "uq_telephony_provider_msp_default",
            "provider_type",
            unique=True,
            postgresql_where=(
                tenant_id.is_(None) & is_default.is_(True) & is_active.is_(True)
            ),
        ),
        # One active tenant default per provider type per tenant
        Index(
            "uq_telephony_provider_tenant_default",
            "tenant_id",
            "provider_type",
            unique=True,
            postgresql_where=(
                tenant_id.isnot(None) & is_default.is_(True) & is_active.is_(True)
            ),
        ),
    )
