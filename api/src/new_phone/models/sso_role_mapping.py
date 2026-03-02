import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class SSORoleMapping(Base):
    __tablename__ = "sso_role_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sso_provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sso_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_group_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pbx_role: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "sso_provider_id",
            "external_group_id",
            name="uq_sso_role_mapping_provider_group",
        ),
    )

    sso_provider = relationship("SSOProvider", back_populates="role_mappings")
