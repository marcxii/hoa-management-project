from sqlalchemy.orm import Mapped, mapped_column, relationship

from hoa.db.base import Base, TenantScopedMixin, TimestampMixin


class Property(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "properties"

    name: Mapped[str] = mapped_column(nullable=False)
    address_line1: Mapped[str] = mapped_column(nullable=False)
    address_line2: Mapped[str | None] = mapped_column(nullable=True)
    city: Mapped[str] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(nullable=False)
    postal_code: Mapped[str] = mapped_column(nullable=False)

    units: Mapped[list["Unit"]] = relationship(  # noqa: F821
        back_populates="property", cascade="all, delete-orphan"
    )
