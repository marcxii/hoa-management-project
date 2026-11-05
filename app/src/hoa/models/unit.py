import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hoa.db.base import Base, TenantScopedMixin, TimestampMixin


class Unit(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "units"

    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_number: Mapped[str] = mapped_column(nullable=False)
    square_feet: Mapped[int | None] = mapped_column(nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(nullable=True)

    property: Mapped["Property"] = relationship(back_populates="units")  # noqa: F821
    residents: Mapped[list["Resident"]] = relationship(  # noqa: F821
        back_populates="unit", cascade="all, delete-orphan"
    )
