# Portal Deployment

The Publishing House Portal is deployed to OpenShift using Ansible with Jinja2-templated manifests, following the same pattern as RCARS.

## Architecture

```
User → Route (TLS) → OAuth Proxy → Next.js Frontend (port 3000)
                                         │
                                    API proxy (/api/v1/*)
                                         │
                                   Backend Service (ClusterIP)
                                         │
                                    FastAPI (port 8080)
                                         │
                                    PostgreSQL (PVC)
```

- **Frontend:** Next.js 16 + PatternFly 6. Exposed via OpenShift Route with OAuth proxy for SSO.
- **Backend:** FastAPI + SQLAlchemy. Internal only (ClusterIP, no external Route).
- **Database:** PostgreSQL 16 with persistent storage.
- **Auth:** OpenShift OAuth proxy on the frontend. Backend trusts internal traffic.

## Prerequisites

- Ansible with `kubernetes.core` collection
- `oc` CLI authenticated to the target cluster (for initial bootstrap)
- GitHub Fine-Grained PAT scoped to `rhpds` org with Contents read access

Install the Ansible collection:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

## Configuration

```bash
cp ansible/vars/dev.yml.example ansible/vars/dev.yml
```

Fill in all `CHANGEME` values:

| Variable | Description |
|----------|-------------|
| `cluster_domain` | OpenShift apps domain (e.g., `apps.mycluster.example.com`) |
| `kubeconfig` | Path to the management SA kubeconfig (after bootstrap) |
| `git_ref` | Git branch to build from (e.g., `main`, `gsd-project`) |
| `pg_password` | PostgreSQL password — generate with `openssl rand -hex 16` |
| `oauth_client_secret` | OAuth client secret — generate with `openssl rand -hex 16` |
| `oauth_cookie_secret` | OAuth cookie secret — generate with `openssl rand -hex 16` |
| `github_repo` | Repo in `owner/name` format (e.g., `rhpds/rhdp-publishing-house-portal`) |
| `github_token` | GitHub PAT for fetching manifests from private repos |
| `rcars_url` | RCARS external URL for frontend links (e.g., `https://rcars-dev.apps.<cluster-domain>/`) |
| `rcars_internal_url` | RCARS cluster-internal URL (e.g., `http://rcars-api.rcars-dev.svc.cluster.local:8080`) |
| `rcars_stages` | RCARS catalog stages to query. Default: `prod`. Set to `prod,zt` or `prod,event,zt` to include other stages. |
| `mcp_route_host` | Hostname for the MCP endpoint Route (e.g., `ph-mcp-dev.apps.<cluster-domain>`) |
| `mcp_api_keys` | Dict of `name: sha256-hash` pairs for MCP API key auth. See [MCP Auth Admin Guide](admin/mcp-auth.md) |

**NEVER commit `dev.yml` or `prod.yml`** — they are gitignored. Only `.example` files are tracked.

## First-Time Deployment

```bash
# 1. Bootstrap management ServiceAccount (one-time, with personal kubeconfig)
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac

# 2. Update dev.yml with the generated mgmt kubeconfig path

# 3. Full deploy (infra + app + builds + migrations)
ansible-playbook ansible/deploy.yml -e env=dev --tags deploy
```

The `deploy` tag runs infra manifests, app manifests, builds, and database migrations in one pass.

## Playbook Tags

| Tag | What It Does | When to Use |
|-----|-------------|-------------|
| `mgmt-rbac` | Bootstrap management SA, ClusterRole, generate kubeconfig | One-time setup |
| `deploy` | Full deploy: infra + app + builds + migrate | Normal deployment |
| `apply` | App manifests only (Deployments, Services, Route) | Config-only changes |
| `builds` | Trigger builds + wait for rollout | Code changes only |
| `build-backend` | Build backend only + rollout | Backend code changes |
| `build-frontend` | Build frontend only + rollout | Frontend code changes |
| `migrate` | Run Alembic migrations in backend pod | Schema changes |

## Subsequent Deploys

```bash
# Full redeploy
ansible-playbook ansible/deploy.yml -e env=dev --tags deploy

# Rebuild only (after code push)
ansible-playbook ansible/deploy.yml -e env=dev --tags builds

# App manifests only (no build)
ansible-playbook ansible/deploy.yml -e env=dev --tags apply

# Schema migration only
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

## Build Triggers

Builds are triggered manually via Ansible tags (`--tags builds`, `--tags build-backend`, `--tags build-frontend`). The BuildConfigs use the `git_ref` from vars (e.g., `gsd-project` for dev, `production` for prod) to determine which branch to build from.

## Container Images

Two Containerfiles at the repo root:

- **`Containerfile.backend`** — UBI9 Python 3.11 multi-stage. Installs requirements, copies app + Alembic. Runs uvicorn on port 8080.
- **`Containerfile.frontend`** — UBI9 Node.js 20 multi-stage. Builds Next.js standalone output. Runs `node server.js` on port 3000.

## Repos

- [rhdp-publishing-house-portal](https://github.com/rhpds/rhdp-publishing-house-portal) — the portal app and deployment manifests
- [rhdp-publishing-house](https://github.com/rhpds/rhdp-publishing-house) — the CLI skills and plugin
