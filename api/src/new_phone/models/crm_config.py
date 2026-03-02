import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base, TimestampMixin


class CRMProviderType(StrEnum):
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    CONNECTWISE = "connectwise"
    ZOHO = "zoho"
    WEBHOOK = "webhook"


class CRMConfig(Base, TimestampMixin):
    __tablename__ = "crm_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(String(30), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3600")
    lookup_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    enrichment_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    enrich_inbound: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    enrich_outbound: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    custom_fields_map: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    tenant = relationship("Tenant", lazy="joined")
