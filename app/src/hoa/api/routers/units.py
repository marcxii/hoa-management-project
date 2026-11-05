from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import get_current_user, require_staff
from hoa.api.utils import get_or_404
from hoa.config import get_settings
from hoa.db.session import get_db
from hoa.models.property import Property
from hoa.models.unit import Unit
from hoa.models.user import User
from hoa.schemas.unit import UnitCreate, UnitRead, UnitUpdate

router = APIRouter(prefix="/api/v1/units", tags=["units"])


@router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    payload: UnitCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Unit:
    settings = get_settings()
    await get_or_404(db, Property, payload.property_id, detail="Property not found")
    unit = Unit(tenant_id=settings.tenant_id, **payload.model_dump())
    db.add(unit)
    await db.flush()
    return unit


@router.get("", response_model=list[UnitRead])
async def list_units(
    property_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Unit]:
    stmt = select(Unit).order_by(Unit.unit_number)
    if property_id is not None:
        stmt = stmt.where(Unit.property_id == property_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{unit_id}", response_model=UnitRead)
async def get_unit(
    unit_id: UUID, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
) -> Unit:
    return await get_or_404(db, Unit, unit_id)


@router.patch("/{unit_id}", response_model=UnitRead)
async def update_unit(
    unit_id: UUID,
    payload: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Unit:
    unit = await get_or_404(db, Unit, unit_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    await db.flush()
    return unit


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: UUID, db: AsyncSession = Depends(get_db), _staff: User = Depends(require_staff)
) -> None:
    unit = await get_or_404(db, Unit, unit_id)
    await db.delete(unit)
