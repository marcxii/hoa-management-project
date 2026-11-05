from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from hoa.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict:
    """Liveness: the process is up. No dependency checks — if this fails,
    Kubernetes restarts the pod, which won't help a downstream DB outage."""
    return {"status": "ok"}


@router.get("/readyz")
async def readiness() -> dict:
    """Readiness: can this pod actually serve traffic right now? Checked
    against the DB directly (not via the tenant-scoped get_db dependency,
    since this doesn't need/want RLS context) so Kubernetes stops routing
    traffic here the moment Postgres is unreachable."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable"
        ) from exc
    return {"status": "ok"}
