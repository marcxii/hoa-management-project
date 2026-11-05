import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hoa.db.base import Base, TenantScopedMixin, TimestampMixin


class Resident(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "residents"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False)
    phone: Mapped[str | None] = mapped_column(nullable=True)
    is_owner: Mapped[bool] = mapped_column(nullable=False, default=False)
    move_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    move_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    unit: Mapped["Unit"] = relationship(back_populates="residents")  # noqa: F821
