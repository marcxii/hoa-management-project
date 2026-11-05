import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hoa.db.base import Base, TenantScopedMixin, TimestampMixin


class InvoiceStatus(enum.StrEnum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"
    void = "void"


class Invoice(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "invoices"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", native_enum=True),
        nullable=False,
        default=InvoiceStatus.unpaid,
    )

    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="invoice", cascade="all, delete-orphan"
    )
