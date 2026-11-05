from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from passlib.context import CryptContext

from hoa.config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, user_id: UUID, role: str, tenant_id: UUID) -> str:
    """Issue a JWT scoped to one user, carrying tenant_id as a claim.

    tenant_id in the token is NOT how we decide which tenant's data to query
    (that's always the deployment's own TENANT_ID, injected via Helm values).
    It's a defense-in-depth check: if a token minted for one tenant's
    deployment is ever presented to a different tenant's deployment, we
    reject it outright in `get_current_user` rather than silently trusting it.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
