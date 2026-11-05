import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hoa.db.base import Base, TenantScopedMixin, TimestampMixin


class PaymentMethod(enum.StrEnum):
    check = "check"
    ach = "ach"
    card = "card"
    cash = "cash"
    other = "other"


class Payment(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", native_enum=True), nullable=False
    )
    reference: Mapped[str | None] = mapped_column(nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")  # noqa: F821
