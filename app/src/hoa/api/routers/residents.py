from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import get_current_resident, require_staff
from hoa.api.utils import get_or_404
from hoa.config import get_settings
from hoa.db.session import get_db
from hoa.models.resident import Resident
from hoa.models.unit import Unit
from hoa.models.user import User
from hoa.schemas.resident import ResidentCreate, ResidentRead, ResidentUpdate

router = APIRouter(prefix="/api/v1/residents", tags=["residents"])


@router.post("", response_model=ResidentRead, status_code=status.HTTP_201_CREATED)
async def create_resident(
    payload: ResidentCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Resident:
    settings = get_settings()
    await get_or_404(db, Unit, payload.unit_id, detail="Unit not found")
    resident = Resident(tenant_id=settings.tenant_id, **payload.model_dump())
    db.add(resident)
    await db.flush()
    return resident


@router.get("", response_model=list[ResidentRead])
async def list_residents(
    unit_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> list[Resident]:
    stmt = select(Resident).order_by(Resident.last_name)
    if unit_id is not None:
        stmt = stmt.where(Resident.unit_id == unit_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/me", response_model=ResidentRead)
async def read_my_resident_record(resident: Resident = Depends(get_current_resident)) -> Resident:
    return resident


@router.get("/{resident_id}", response_model=ResidentRead)
async def get_resident(
    resident_id: UUID, db: AsyncSession = Depends(get_db), _staff: User = Depends(require_staff)
) -> Resident:
    return await get_or_404(db, Resident, resident_id)


@router.patch("/{resident_id}", response_model=ResidentRead)
async def update_resident(
    resident_id: UUID,
    payload: ResidentUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Resident:
    resident = await get_or_404(db, Resident, resident_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resident, field, value)
    await db.flush()
    return resident


@router.delete("/{resident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resident(
    resident_id: UUID, db: AsyncSession = Depends(get_db), _staff: User = Depends(require_staff)
) -> None:
    resident = await get_or_404(db, Resident, resident_id)
    await db.delete(resident)
