import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class CWCompanyMapping(Base):
    __tablename__ = "cw_company_mappings"
    __table_args__ = (
        CheckConstraint("extension_id IS NOT NULL OR did_id IS NOT NULL", name="ck_cw_mapping_has_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cw_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cw_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cw_company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cw_company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True
    )
    did_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dids.id", ondelete="SET NULL"), nullable=True
    )

    cw_config = relationship("CWConfig", back_populates="company_mappings", lazy="joined")
    extension = relationship("Extension", lazy="joined")
    did = relationship("DID", lazy="joined")
