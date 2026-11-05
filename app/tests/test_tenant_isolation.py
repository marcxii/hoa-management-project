"""Proves the row-level security story end to end.

This is the single most important test in the project: the whole multi-
tenancy pitch rests on Postgres itself refusing to hand back — or accept —
rows for the wrong tenant, not on every query remembering a WHERE clause.
"""

import uuid

import pytest
from conftest import TENANT_A, TENANT_B, TEST_APP_DATABASE_URL, tenant_app_client
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine


async def _set_tenant(conn, tenant_id: uuid.UUID) -> None:
    await conn.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def test_rls_hides_rows_from_other_tenants_even_without_a_where_clause():
    engine = create_async_engine(TEST_APP_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await _set_tenant(conn, TENANT_A)
            await conn.execute(
                text(
                    "INSERT INTO properties (tenant_id, name, address_line1, city, state, "
                    "postal_code) VALUES (:tenant_id, 'Tenant A HQ', '1 Main St', 'Austin', "
                    "'TX', '78701')"
                ),
                {"tenant_id": str(TENANT_A)},
            )

        # A query with NO tenant filter at all — exactly the kind of mistake
        # app code could make. RLS, not the query, is what keeps this safe.
        async with engine.begin() as conn:
            await _set_tenant(conn, TENANT_A)
            as_tenant_a = (await conn.execute(text("SELECT COUNT(*) FROM properties"))).scalar_one()

        async with engine.begin() as conn:
            await _set_tenant(conn, TENANT_B)
            as_tenant_b = (await conn.execute(text("SELECT COUNT(*) FROM properties"))).scalar_one()

        assert as_tenant_a == 1
        assert as_tenant_b == 0
    finally:
        await engine.dispose()


async def test_rls_blocks_inserting_a_row_under_a_different_tenant_id():
    """Defense-in-depth: even if application code had a bug and tried to
    write a row tagged with the wrong tenant_id, the WITH CHECK clause on
    the RLS policy rejects it outright rather than silently corrupting data."""
    engine = create_async_engine(TEST_APP_DATABASE_URL)
    try:
        with pytest.raises(DBAPIError, match="row-level security"):
            async with engine.begin() as conn:
                await _set_tenant(conn, TENANT_A)
                await conn.execute(
                    text(
                        "INSERT INTO properties (tenant_id, name, address_line1, city, state, "
                        "postal_code) VALUES (:tenant_id, 'Smuggled Row', '1 Main St', "
                        "'Austin', 'TX', '78701')"
                    ),
                    # Session is set to tenant A, but the row claims tenant B.
                    {"tenant_id": str(TENANT_B)},
                )
    finally:
        await engine.dispose()


async def test_api_level_isolation_between_two_tenant_deployments():
    """The same proof, but through the HTTP API with two separate app
    instances (standing in for two separate namespace deployments) pointed
    at the same shared Postgres.

    The two tenants' app instances are exercised strictly one at a time —
    see the docstring on tenant_app_client for why they can never both be
    "live" at once within a single test process."""
    from helpers import auth_headers, login, seed_user

    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_B,
        email="board@oakwood.test",
        password="correct-horse",
        role="board_member",
    )
    async with tenant_app_client(TENANT_B) as client_b:
        token_b = await login(client_b, "board@oakwood.test", "correct-horse")
        await client_b.post(
            "/api/v1/properties",
            json={
                "name": "Oakwood Clubhouse",
                "address_line1": "200 Oak St",
                "city": "Austin",
                "state": "TX",
                "postal_code": "78702",
            },
            headers=auth_headers(token_b),
        )

    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_A,
        email="board@sunsetridge.test",
        password="correct-horse",
        role="board_member",
    )
    async with tenant_app_client(TENANT_A) as client_a:
        token_a = await login(client_a, "board@sunsetridge.test", "correct-horse")
        response = await client_a.get("/api/v1/properties", headers=auth_headers(token_a))

    assert response.status_code == 200
    assert response.json() == []
