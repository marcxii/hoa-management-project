#!/bin/bash
# Runs automatically, exactly once, the first time Postgres initializes its
# data directory (standard docker-entrypoint-initdb.d behavior — this file is
# mounted at that path by both docker-compose and the K8s StatefulSet).
#
# This is deliberately separate from the Alembic migrations in app/alembic:
# role creation is one-time database bootstrap, not a versioned schema
# change, and Alembic (connecting as hoa_migrator) can't create the very
# role it needs to connect as.
#
# hoa_migrator owns the schema/tables (via CREATE on public) and runs
# migrations. hoa_app is the app's runtime role and deliberately does NOT
# own anything — Postgres bypasses row-level security for table owners and
# superusers, so a non-owner role is what makes RLS policies actually apply.
set -euo pipefail

: "${HOA_MIGRATOR_PASSWORD:?HOA_MIGRATOR_PASSWORD must be set}"
: "${HOA_APP_PASSWORD:?HOA_APP_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE ROLE hoa_migrator LOGIN PASSWORD '${HOA_MIGRATOR_PASSWORD}';
  CREATE ROLE hoa_app LOGIN PASSWORD '${HOA_APP_PASSWORD}';

  GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO hoa_migrator, hoa_app;
  GRANT CREATE, USAGE ON SCHEMA public TO hoa_migrator;
  GRANT USAGE ON SCHEMA public TO hoa_app;
EOSQL
