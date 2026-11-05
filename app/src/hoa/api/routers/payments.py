from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import get_current_user, get_resident_unit_ids, require_staff
from hoa.api.utils import get_or_404
from hoa.db.session import get_db
from hoa.models.invoice import Invoice, InvoiceStatus
from hoa.models.payment import Payment
from hoa.models.user import User, UserRole
from hoa.schemas.payment import PaymentCreate, PaymentRead

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


async def _recalculate_invoice_status(db: AsyncSession, invoice: Invoice) -> None:
    """Derives invoice.status from the sum of recorded payments.

    Kept as an explicit recalculation (rather than a generated/computed
    column) so the business rule is easy to point to and test in isolation —
    this is the one bit of real HOA domain logic in an otherwise
    infra-focused project.
    """
    if invoice.status == InvoiceStatus.void:
        return
    result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(
            Payment.invoice_id == invoice.id
        )
    )
    total_paid = result.scalar_one()
    if total_paid >= invoice.amount_cents:
        invoice.status = InvoiceStatus.paid
    elif total_paid > 0:
        invoice.status = InvoiceStatus.partial
    else:
        invoice.status = InvoiceStatus.unpaid


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Payment:
    invoice = await get_or_404(db, Invoice, payload.invoice_id, detail="Invoice not found")
    payment = Payment(tenant_id=invoice.tenant_id, **payload.model_dump())
    db.add(payment)
    await db.flush()
    await _recalculate_invoice_status(db, invoice)
    await db.flush()
    return payment


@router.get("", response_model=list[PaymentRead])
async def list_payments(
    invoice_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.paid_at.desc())
    if invoice_id is not None:
        stmt = stmt.where(Payment.invoice_id == invoice_id)
    if user.role == UserRole.resident:
        allowed_units = await get_resident_unit_ids(user, db)
        stmt = stmt.join(Invoice, Invoice.id == Payment.invoice_id).where(
            Invoice.unit_id.in_(allowed_units)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Payment:
    payment = await get_or_404(db, Payment, payment_id)
    if user.role == UserRole.resident:
        invoice = await db.get(Invoice, payment.invoice_id)
        allowed_units = await get_resident_unit_ids(user, db)
        if invoice is None or invoice.unit_id not in allowed_units:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment
