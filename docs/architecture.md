# Architecture

## Tenancy: two layers, two different isolation strategies

```
                         ┌─────────────────────────────────────┐
                         │              ArgoCD                  │
                         │  ApplicationSet watches git files:   │
                         │  infra/helm/hoa-app/tenants/*.yaml    │
                         └───────────────┬───────────────────────┘
                                          │ stamps out one Application
                                          │ per tenant file
              ┌───────────────────────────┼───────────────────────────┐
              ▼                            ▼                            ▼
   ns: sunset-ridge              ns: oakwood                 ns: pinecrest
   ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
   │ hoa-app Deployment│         │ hoa-app Deployment│        │ hoa-app Deployment│
   │ TENANT_ID=1111... │         │ TENANT_ID=2222... │        │ TENANT_ID=3333... │
   │ NetworkPolicy      │        │ NetworkPolicy      │       │ NetworkPolicy      │
   │ ResourceQuota       │       │ ResourceQuota       │      │ ResourceQuota       │
   └─────────┬───────────┘       └─────────┬───────────┘      └─────────┬───────────┘
             │                             │                            │
             └─────────────────┬───────────┴────────────────────────────┘
                                ▼
                     ns: hoa-platform
                     ┌───────────────────────┐
                     │   Postgres (shared)     │
                     │   RLS policy per table: │
                     │   tenant_id = current_  │
                     │   setting('app.tenant_  │
                     │   id')                  │
                     └───────────────────────┘
```

- **Infra layer (hard boundary): namespace per tenant.** Independent
  Deployments, NetworkPolicies, ResourceQuotas. A compromised or buggy pod
  in one tenant's namespace has no network path to another tenant's
  namespace — confirmed by direct test (`kubectl exec` from one tenant's
  pod to another's Service times out).
- **Data layer (soft boundary, DB-enforced): shared Postgres + RLS.** One
  database, every table carries `tenant_id`, every table has an RLS policy
  `USING/WITH CHECK (tenant_id = current_setting('app.tenant_id'))`. The
  app sets that setting once per transaction via `set_config(..., true)` —
  the `true` makes it behave like `SET LOCAL`, scoped to the transaction,
  safe under connection pooling where a pooled connection might serve a
  different tenant's transaction moments later.

Each tenant's Deployment gets `TENANT_ID` baked in via Helm values —
there's no subdomain/JWT-claim resolution step, because the namespace a
request lands in already answers "whose data is this."

## Why RLS, not just `WHERE tenant_id = ...`

Application code can forget a `WHERE` clause. Postgres can't forget its own
policy. `app/tests/test_tenant_isolation.py` proves this directly: a query
with *no* tenant filter at all still returns zero rows for the wrong
tenant, and an INSERT tagged with the wrong `tenant_id` is rejected outright
by the `WITH CHECK` clause — not by application validation.

Two Postgres roles make this work:
- `hoa_migrator` owns the schema, runs Alembic migrations.
- `hoa_app` is what the running app connects as — a non-owner role, because
  **RLS is bypassed for table owners and superusers.** This is the single
  most common way to accidentally defeat RLS; using a separate runtime role
  avoids it entirely.

## GitOps flow

1. A tenant is a file: `infra/helm/hoa-app/tenants/<name>.yaml` (tenant ID,
   ingress host, DB credentials).
2. ArgoCD's `ApplicationSet` (`infra/argocd/applicationset-tenants.yaml`)
   uses a git `files` generator over that directory. Each matched file
   becomes one `Application`: its own namespace (`CreateNamespace=true`),
   its own Helm release of the one shared chart (`infra/helm/hoa-app`),
   using that file as the values override.
3. Commit + push a new tenant file → ArgoCD's generator picks it up on its
   next poll (default ~3 min; a repo webhook would make this instant) →
   namespace + release appear with no `kubectl`/`helm` command run by a
   human.
4. The shared Postgres (`infra/argocd/postgres-app.yaml`) is a separate,
   plain-manifest `Application` — it isn't per-tenant, so it doesn't go
   through the tenant `ApplicationSet`.
5. One `Application` (`hoa-root`, applied manually exactly once via
   `infra/argocd/bootstrap/root-app.yaml`) is the "app of apps": it watches
   `infra/argocd/` itself and applies the `ApplicationSet` and the Postgres
   `Application` as data. After that one manual step, everything is git.

## Migrations as a Helm hook

Each tenant release includes a `pre-install,pre-upgrade` hook `Job`
(`infra/helm/hoa-app/templates/job-migrate.yaml`) that runs
`alembic upgrade head` as `hoa_migrator` before the Deployment rolls. It
sets its DB URL inline rather than via the chart's `Secret` resource,
because hook resources run *before* a release's regular resources exist —
the `Secret` wouldn't be there yet for the Job to reference.
