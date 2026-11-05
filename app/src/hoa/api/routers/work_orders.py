from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import get_current_user, get_resident_unit_ids, require_staff
from hoa.api.utils import get_or_404
from hoa.config import get_settings
from hoa.db.session import get_db
from hoa.models.user import User, UserRole
from hoa.models.work_order import WorkOrder, WorkOrderStatus
from hoa.schemas.work_order import WorkOrderCreate, WorkOrderRead, WorkOrderUpdate

router = APIRouter(prefix="/api/v1/work-orders", tags=["work-orders"])


@router.post("", response_model=WorkOrderRead, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    payload: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkOrder:
    """Residents may only file work orders for their own unit; staff may file
    one for any unit in the tenant (e.g. on a resident's behalf)."""
    settings = get_settings()
    requested_by_resident_id = None
    if user.role == UserRole.resident:
        allowed_units = await get_resident_unit_ids(user, db)
        if payload.unit_id not in allowed_units:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only file work orders for your own unit",
            )
        requested_by_resident_id = user.resident_id

    work_order = WorkOrder(
        tenant_id=settings.tenant_id,
        requested_by_resident_id=requested_by_resident_id,
        **payload.model_dump(),
    )
    db.add(work_order)
    await db.flush()
    return work_order


@router.get("", response_model=list[WorkOrderRead])
async def list_work_orders(
    unit_id: UUID | None = None,
    status_filter: WorkOrderStatus | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WorkOrder]:
    stmt = select(WorkOrder).order_by(WorkOrder.created_at.desc())
    if user.role == UserRole.resident:
        allowed_units = await get_resident_unit_ids(user, db)
        stmt = stmt.where(WorkOrder.unit_id.in_(allowed_units))
    elif unit_id is not None:
        stmt = stmt.where(WorkOrder.unit_id == unit_id)
    if status_filter is not None:
        stmt = stmt.where(WorkOrder.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{work_order_id}", response_model=WorkOrderRead)
async def get_work_order(
    work_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkOrder:
    work_order = await get_or_404(db, WorkOrder, work_order_id)
    if user.role == UserRole.resident:
        allowed_units = await get_resident_unit_ids(user, db)
        if work_order.unit_id not in allowed_units:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found"
            )
    return work_order


@router.patch("/{work_order_id}", response_model=WorkOrderRead)
async def update_work_order(
    work_order_id: UUID,
    payload: WorkOrderUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> WorkOrder:
    """Status/assignment changes are staff-only — residents can file and view
    their own requests but not mark them in-progress/completed themselves."""
    work_order = await get_or_404(db, WorkOrder, work_order_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(work_order, field, value)
    if updates.get("status") == WorkOrderStatus.completed and work_order.completed_at is None:
        work_order.completed_at = datetime.now(UTC)
    work_order.updated_at = datetime.now(UTC)
    await db.flush()
    return work_order
