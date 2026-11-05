from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import get_current_user, get_resident_unit_ids, require_staff
from hoa.api.utils import get_or_404
from hoa.config import get_settings
from hoa.db.session import get_db
from hoa.models.invoice import Invoice
from hoa.models.unit import Unit
from hoa.models.user import User, UserRole
from hoa.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceUpdate

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Invoice:
    settings = get_settings()
    await get_or_404(db, Unit, payload.unit_id, detail="Unit not found")
    invoice = Invoice(tenant_id=settings.tenant_id, **payload.model_dump())
    db.add(invoice)
    await db.flush()
    return invoice


@router.get("", response_model=list[InvoiceRead])
async def list_invoices(
    unit_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Invoice]:
    """Staff see every invoice (optionally filtered by unit); residents only
    ever see invoices for their own unit, regardless of what unit_id they pass."""
    stmt = select(Invoice).order_by(Invoice.due_date.desc())
    if user.role == UserRole.resident:
        allowed_units = await get_resident_unit_ids(user, db)
        stmt = stmt.where(Invoice.unit_id.in_(allowed_units))
    elif unit_id is not None:
        stmt = stmt.where(Invoice.unit_id == unit_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Invoice:
    invoice = await get_or_404(db, Invoice, invoice_id)
    if user.role == UserRole.resident:
        allowed_units = await get_resident_unit_ids(user, db)
        if invoice.unit_id not in allowed_units:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceRead)
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Invoice:
    invoice = await get_or_404(db, Invoice, invoice_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    await db.flush()
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID, db: AsyncSession = Depends(get_db), _staff: User = Depends(require_staff)
) -> None:
    invoice = await get_or_404(db, Invoice, invoice_id)
    await db.delete(invoice)
