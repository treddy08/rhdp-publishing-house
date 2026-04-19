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

- **Frontend:** Next.js 15 + PatternFly 6. Exposed via OpenShift Route with OAuth proxy for SSO.
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
| `pg_password` | PostgreSQL password — generate with `openssl rand -hex 16` |
| `oauth_client_secret` | OAuth client secret — generate with `openssl rand -hex 16` |
| `oauth_cookie_secret` | OAuth cookie secret — generate with `openssl rand -hex 16` |
| `webhook_secret` | GitHub webhook secret — generate with `openssl rand -hex 16` |
| `github_repo` | Repo in `owner/name` format (e.g., `rhpds/rhdp-publishing-house-portal`) |
| `github_token` | GitHub PAT for fetching manifests from private repos |

**NEVER commit `dev.yml` or `prod.yml`** — they are gitignored. Only `.example` files are tracked.

## First-Time Deployment

```bash
# 1. Bootstrap management ServiceAccount (one-time, with personal kubeconfig)
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac

# 2. Update dev.yml with the generated mgmt kubeconfig path

# 3. Full deploy (infra + builds + app manifests + migrations)
ansible-playbook ansible/deploy.yml -e env=dev --tags update

# 4. Run database migrations
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate

# 5. Get webhook URLs
ansible-playbook ansible/deploy.yml -e env=dev --tags webhooks
```

Configure both webhook URLs (backend + frontend) in the GitHub repo settings:
`rhpds/rhdp-publishing-house-portal` → Settings → Webhooks → Add webhook.
Content type: `application/json`. Secret: your `webhook_secret` value.

## Playbook Tags

| Tag | What It Does | When to Use |
|-----|-------------|-------------|
| `mgmt-rbac` | Bootstrap management SA, ClusterRole, generate kubeconfig | One-time setup |
| `bootstrap` | Namespace + infra manifests (PG, BuildConfigs, Secrets, OAuth) | First deploy or infra changes |
| `apply` | App manifests (Deployments, Services, Route) | Config-only changes |
| `update` | bootstrap + builds + apply + migrate + webhooks | Normal deployment |
| `builds` | Trigger builds + wait for rollout | Code changes only |
| `migrate` | Run Alembic migrations in backend pod | Schema changes |
| `webhooks` | Print GitHub webhook URLs | Reference |

## Subsequent Deploys

```bash
# Full redeploy
ansible-playbook ansible/deploy.yml -e env=dev --tags update

# Rebuild only (after code push)
ansible-playbook ansible/deploy.yml -e env=dev --tags builds

# Schema migration only
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

## Automated Builds

After configuring GitHub webhooks, pushes to the configured branch (`main` for dev, `production` for prod) automatically trigger both BuildConfigs. Images are rebuilt and Deployments roll out via ImageStream triggers.

## Container Images

Two Containerfiles at the repo root:

- **`Containerfile.backend`** — UBI9 Python 3.11 multi-stage. Installs requirements, copies app + Alembic. Runs uvicorn on port 8080.
- **`Containerfile.frontend`** — UBI9 Node.js 20 multi-stage. Builds Next.js standalone output. Runs `node server.js` on port 3000.

## Repos

- [rhdp-publishing-house-portal](https://github.com/rhpds/rhdp-publishing-house-portal) — the portal app and deployment manifests
- [rhdp-publishing-house](https://github.com/rhpds/rhdp-publishing-house) — the CLI skills and plugin
