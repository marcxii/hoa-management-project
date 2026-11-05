import logging

import structlog
from fastapi import FastAPI

from hoa.api.routers import (
    auth,
    invoices,
    payments,
    properties,
    residents,
    units,
    users,
    work_orders,
)
from hoa.config import get_settings
from hoa.health import router as health_router


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(format="%(message)s", level=settings.log_level)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
    )


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="HOA Management API",
        description=f"Single-tenant deployment (tenant_id={settings.tenant_id})",
        version="0.1.0",
    )

    app.include_router(health_router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(properties.router)
    app.include_router(units.router)
    app.include_router(residents.router)
    app.include_router(invoices.router)
    app.include_router(payments.router)
    app.include_router(work_orders.router)

    return app


app = create_app()
