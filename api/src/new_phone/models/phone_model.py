import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from new_phone.db.base import Base, TimestampMixin


class PhoneModel(Base, TimestampMixin):
    """Global reference data for supported phone models (no tenant scope)."""

    __tablename__ = "phone_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manufacturer: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_family: Mapped[str] = mapped_column(String(50), nullable=False)

    max_line_keys: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_expansion_keys: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_expansion_modules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    has_color_screen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_wifi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_bluetooth: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_expansion_port: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_poe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_gigabit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    firmware_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
