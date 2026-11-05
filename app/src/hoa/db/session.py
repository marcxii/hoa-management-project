from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hoa.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, autoflush=False
        )
    return _session_factory


async def reset_engine_for_tests() -> None:
    """Disposes the cached engine/session factory so a new DATABASE_URL (or
    a fresh connection pool) takes effect. Only meant to be called from
    tests — in a real deployment DATABASE_URL never changes at runtime."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a tenant-scoped DB session.

    Every request gets exactly one transaction. Before any application query
    runs, we stamp the tenant into the transaction-local Postgres setting
    `app.tenant_id` using `set_config(..., is_local=true)` — the third
    argument makes it behave like `SET LOCAL`: it only lives for the duration
    of this transaction and is automatically discarded on commit/rollback.

    This matters because the app will eventually sit behind PgBouncer in
    transaction-pooling mode, where the physical connection handed to this
    transaction may be reused by a *different tenant's* transaction moments
    later. A plain `SET` (session-scoped) would leak across that boundary;
    `set_config(..., true)` cannot.

    We also use `set_config` instead of a literal `SET app.tenant_id = '...'`
    string because `SET` does not accept bound parameters in asyncpg —
    `set_config` is a normal SQL function call and so is safe from injection
    even though tenant_id itself is trusted, server-side configuration here
    (not user input), not unsanitized input.
    """
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(settings.tenant_id)},
            )
            yield session
