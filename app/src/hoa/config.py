from functools import lru_cache
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, sourced entirely from environment variables.

    TENANT_ID is the single most important setting in this app: because every
    deployment of this service is pinned to exactly one HOA (namespace-per-tenant
    at the infra layer), the tenant never needs to be derived from the request —
    it's baked into the Deployment via Helm values. Every DB transaction stamps
    this value into Postgres via `set_config('app.tenant_id', ...)`, which is what
    the row-level security policies key off of.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    log_level: str = "INFO"

    tenant_id: UUID

    # Runtime DB credentials connect as the restricted `hoa_app` role, which is
    # deliberately NOT the owner of the tables — Postgres RLS is bypassed for
    # table owners/superusers, so using a non-owner role here is what makes the
    # isolation policies actually take effect.
    database_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    cors_allow_origins: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
