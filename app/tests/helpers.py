import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from hoa.core.security import hash_password


async def seed_user(
    database_url: str,
    tenant_id: uuid.UUID,
    *,
    email: str,
    password: str,
    role: str,
    resident_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Inserts a user directly via SQL, bypassing the API.

    Every account in this system (even the first admin) has to come from
    somewhere other than a staff-only "create user" endpoint — in real
    deployments that's scripts/seed.py; here it's this helper. Connects as
    hoa_app (the same role the app uses) and sets app.tenant_id first, so
    this insert is subject to the exact same RLS WITH CHECK policy the app
    would hit.
    """
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
            result = await conn.execute(
                text(
                    """
                    INSERT INTO users (tenant_id, email, hashed_password, role, resident_id)
                    VALUES (:tenant_id, :email, :hashed_password, :role, :resident_id)
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": str(tenant_id),
                    "email": email,
                    "hashed_password": hash_password(password),
                    "role": role,
                    "resident_id": str(resident_id) if resident_id else None,
                },
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


async def login(client, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
