# Runbook

## Local setup from scratch

```bash
# 1. Cluster
kind create cluster --config infra/kind/kind-config.yaml

# 2. Ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller --timeout=180s

# 3. App image — kind can't pull from your local Docker daemon directly
docker build -t hoa-app:local app/
kind load docker-image hoa-app:local --name hoa

# 4. ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.2/manifests/install.yaml
kubectl -n argocd wait --for=condition=available --timeout=180s deployment --all

# 5. Bootstrap — the one manual step; everything after this is a git commit
kubectl apply -f infra/argocd/bootstrap/root-app.yaml
```

Then add `127.0.0.1` entries to `/etc/hosts` for each tenant host (or just
pass `-H "Host: <tenant>.hoa.local"` with curl, which is what the examples
below do, so you don't have to edit `/etc/hosts` for a quick check):

```bash
curl -s -H "Host: sunset-ridge.hoa.local" http://localhost/healthz
```

## Adding a tenant

1. Copy `infra/helm/hoa-app/tenants/sunset-ridge.yaml` to
   `infra/helm/hoa-app/tenants/<new-name>.yaml`.
2. Set a fresh `tenant.id` (any UUID — `uuidgen` works), `tenant.name`
   (must match the filename), and `ingress.host`.
3. Commit and push.
4. ArgoCD's `ApplicationSet` picks it up on its next git poll (force it
   immediately with `kubectl -n argocd patch applicationset hoa-tenants
   --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'`
   if you don't want to wait).

## Checking ArgoCD state

```bash
kubectl -n argocd get applications
kubectl -n argocd get applicationset hoa-tenants
```

`argocd-server` isn't exposed outside the cluster by default here — for the
UI, `kubectl -n argocd port-forward svc/argocd-server 8080:443` and open
`https://localhost:8080`. Initial admin password:
`kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d`

## Seeding the first user for a tenant

There's no self-service signup — the first admin/board account for a
tenant has to be inserted directly (see `app/tests/helpers.py::seed_user`
for the same pattern used in tests):

```bash
kubectl -n hoa-platform exec -it postgres-0 -- psql -U postgres -d hoa
```
```sql
SELECT set_config('app.tenant_id', '<tenant-uuid>', false);
INSERT INTO users (tenant_id, email, hashed_password, role)
VALUES ('<tenant-uuid>', 'board@example.com', '<argon2-hash>', 'board_member');
```

(Running as the `postgres` superuser bypasses RLS, which is exactly what
bootstrap seeding needs — just don't use that connection for anything else.)

## Tearing down

```bash
kind delete cluster --name hoa
```

Everything — ArgoCD, every tenant namespace, Postgres — lives inside the
kind cluster; nothing persists outside it (no cloud resources exist until
Phase 6/EKS is deliberately applied).
