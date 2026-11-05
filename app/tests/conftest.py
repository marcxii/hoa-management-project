import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import hoa.config as config_module
import hoa.db.session as session_module

# These default to the credentials docker-compose.yml provisions via
# infra/postgres/init.sh. Override with env vars to point tests at a
# different Postgres (e.g. in CI).
TEST_APP_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://hoa_app:app_dev_password@localhost:55432/hoa"
)
TEST_MIGRATOR_DATABASE_URL = os.environ.get(
    "TEST_MIGRATOR_DATABASE_URL",
    "postgresql+asyncpg://hoa_migrator:migrator_dev_password@localhost:55432/hoa",
)
TEST_JWT_SECRET = "test-secret-at-least-32-bytes-long-xx"

TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

# Child-to-parent order doesn't matter for TRUNCATE ... CASCADE, but listing
# them explicitly documents what a test might leave behind.
_TABLES = ["work_orders", "payments", "invoices", "users", "residents", "units", "properties"]


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncGenerator[None, None]:
    """Truncates every tenant-scoped table before each test, using the
    migrator role so cleanup isn't itself subject to RLS — a test may have
    left behind rows for any tenant."""
    engine = create_async_engine(TEST_MIGRATOR_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(_TABLES)} CASCADE"))
    await engine.dispose()
    yield


def _set_tenant_env(tenant_id: uuid.UUID) -> None:
    os.environ["TENANT_ID"] = str(tenant_id)
    os.environ["DATABASE_URL"] = TEST_APP_DATABASE_URL
    os.environ["JWT_SECRET"] = TEST_JWT_SECRET
    config_module.get_settings.cache_clear()


@asynccontextmanager
async def tenant_app_client(tenant_id: uuid.UUID) -> AsyncGenerator[AsyncClient, None]:
    """Spins up a fresh app instance pinned to one tenant.

    Settings are read from process env vars and cached process-wide
    (hoa.config.get_settings), which is correct for production — one tenant
    per process, env vars never change at runtime — but means two of these
    context managers must never be open *at the same time* in one pytest
    process: whichever one set the env vars last would silently "win" for
    both. Use this strictly one tenant at a time (see
    test_tenant_isolation.py for the pattern), never as two simultaneously
    held fixtures.
    """
    _set_tenant_env(tenant_id)
    await session_module.reset_engine_for_tests()

    from hoa.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await session_module.reset_engine_for_tests()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """An HTTP client talking to a fresh app instance pinned to TENANT_A —
    the tenant used by every test that isn't specifically about isolation."""
    async with tenant_app_client(TENANT_A) as c:
        yield c
