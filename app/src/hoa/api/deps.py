from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoa.config import get_settings
from hoa.core.security import decode_access_token
from hoa.db.session import get_db
from hoa.models.resident import Resident
from hoa.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    settings = get_settings()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise CREDENTIALS_ERROR from None

    # Defense-in-depth: a token minted for one tenant's deployment must never
    # be honored by a different tenant's deployment, even though in normal
    # operation a token can only ever reach the deployment it was issued by
    # (separate namespaces, separate ingress hosts).
    if payload.get("tenant_id") != str(settings.tenant_id):
        raise CREDENTIALS_ERROR

    user_id = payload.get("sub")
    if user_id is None:
        raise CREDENTIALS_ERROR

    user = await db.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


async def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.admin, UserRole.board_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires board/admin access",
        )
    return user


async def get_current_resident(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Resident:
    """Resolves the resident record tied to the logged-in user.

    Only meaningful for role == resident; staff accounts have no resident_id.
    """
    if user.role != UserRole.resident or user.resident_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a resident account",
        )
    resident = await db.get(Resident, user.resident_id)
    if resident is None:
        raise CREDENTIALS_ERROR
    return resident


async def get_resident_unit_ids(user: User, db: AsyncSession) -> list[UUID]:
    """Unit IDs a resident is allowed to see — just their own unit today, but
    kept as a list/helper in case a resident is ever linked to multiple units.
    """
    if user.resident_id is None:
        return []
    result = await db.execute(select(Resident.unit_id).where(Resident.id == user.resident_id))
    unit_id = result.scalar_one_or_none()
    return [unit_id] if unit_id else []
