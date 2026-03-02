import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from new_phone.db.base import Base


class UserSSOLink(Base):
    __tablename__ = "user_sso_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sso_provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sso_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_email: Mapped[str] = mapped_column(String(320), nullable=False)
    last_sso_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "sso_provider_id",
            "external_user_id",
            name="uq_user_sso_link_provider_ext_user",
        ),
    )

    user = relationship("User", back_populates="sso_links")
    sso_provider = relationship("SSOProvider")
