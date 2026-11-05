from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.api.deps import require_staff
from hoa.config import get_settings
from hoa.core.security import hash_password
from hoa.db.session import get_db
from hoa.models.user import User
from hoa.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    settings = get_settings()
    user = User(
        tenant_id=settings.tenant_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        resident_id=payload.resident_id,
    )
    db.add(user)
    await db.flush()
    return user


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db), _staff: User = Depends(require_staff)
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID, db: AsyncSession = Depends(get_db), _staff: User = Depends(require_staff)
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
