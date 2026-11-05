from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import get_current_user, require_staff
from hoa.api.utils import get_or_404
from hoa.config import get_settings
from hoa.db.session import get_db
from hoa.models.property import Property
from hoa.models.user import User
from hoa.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Property:
    settings = get_settings()
    prop = Property(tenant_id=settings.tenant_id, **payload.model_dump())
    db.add(prop)
    await db.flush()
    return prop


@router.get("", response_model=list[PropertyRead])
async def list_properties(
    db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
) -> list[Property]:
    result = await db.execute(select(Property).order_by(Property.name))
    return list(result.scalars().all())


@router.get("/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Property:
    return await get_or_404(db, Property, property_id)


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Property:
    prop = await get_or_404(db, Property, property_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    await db.flush()
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> None:
    prop = await get_or_404(db, Property, property_id)
    await db.delete(prop)
