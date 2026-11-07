# HOA Management Platform

A multi-tenant HOA (homeowners association) management API, built as an
infrastructure-focused portfolio project. The application itself (FastAPI,
JSON-only) is intentionally lean — the point of this project is the
GitOps/Kubernetes/Helm/ArgoCD layer around it.

## Tenancy model

Multi-tenancy is split across two layers, deliberately using a different
isolation strategy at each:

- **Infra layer — namespace per tenant.** Each HOA gets its own Kubernetes
  namespace, its own Deployment, its own resource quota. ArgoCD manages this
  via an ApplicationSet: adding a tenant is adding one YAML file to
  `infra/argocd/tenants/`.
- **Data layer — shared Postgres + row-level security.** All tenants share
  one Postgres instance. Every table carries `tenant_id`, and Postgres RLS
  policies — not application `WHERE` clauses — are what actually prevent one
  tenant's deployment from reading or writing another tenant's rows. See
  `app/alembic/versions/0001_initial_schema_with_rls.py` and
  `app/tests/test_tenant_isolation.py` for the policy definitions and the
  tests proving they hold.

Each tenant's app deployment gets its own `TENANT_ID` injected via Helm
values — the app never has to resolve "which tenant is this?" from a
subdomain or JWT claim, because the namespace it's running in already
answers that question.

## Repo layout

```
app/        FastAPI service, Alembic migrations, tests
infra/
  helm/      One Helm chart for the app, reused across every tenant release
  postgres/  Plain K8s manifests for the one shared Postgres instance
  argocd/    App-of-apps root + the ApplicationSet that stamps out tenants
  kind/      Local cluster config
  terraform/ EKS provisioning — written, not applied until a live demo is wanted
docs/        Architecture notes and operational runbook
```

## Local development (no Kubernetes required yet)

```bash
docker compose up -d postgres
docker compose run --rm migrate          # alembic upgrade head
docker compose up -d app-sunset-ridge app-oakwood
```

This brings up one shared Postgres and **two** separate app containers —
`app-sunset-ridge` (port 8001) and `app-oakwood` (port 8002) — standing in
for two tenant namespaces, so the isolation story is visible without a
cluster at all. Swagger docs: `http://localhost:8001/docs`.

> Postgres is exposed on host port **55432**, not 5432, to avoid clashing
> with anything already running locally.

## Running the tests

```bash
cd app
uv sync --group dev
docker compose -f ../docker-compose.yml up -d postgres
MIGRATOR_DATABASE_URL="postgresql+asyncpg://hoa_migrator:migrator_dev_password@localhost:55432/hoa" uv run alembic upgrade head
uv run pytest
```

The most important test is `tests/test_tenant_isolation.py` — it proves RLS
blocks cross-tenant reads *even with no `WHERE tenant_id = ...` in the
query*, and rejects writes tagged with the wrong tenant.

## Status

- [x] FastAPI app: properties/units/residents, dues/invoices/payments,
      maintenance work orders — JWT auth, role-based access (admin /
      board_member / resident), RLS-backed tenant isolation
- [x] Local `kind` cluster + Helm chart — namespace-per-tenant, NetworkPolicy,
      ResourceQuota, verified live (see `docs/runbook.md`)
- [x] ArgoCD + ApplicationSet GitOps — adding a tenant is one file + a git
      push, no `kubectl`/`helm` (see `docs/architecture.md`)
- [ ] CI (GitHub Actions)
- [ ] Observability (Prometheus/Grafana), structured logging
- [ ] EKS (Terraform written, applied only for live demos — real AWS cost)

See `docs/architecture.md` for the tenancy model and `docs/runbook.md` for
cluster setup, adding a tenant, and teardown.
