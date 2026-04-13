# RHDP Publishing House Dashboard

A web dashboard that provides cross-project visibility into the Publishing House content lifecycle. While individual authors interact with the CLI skills, the dashboard gives managers and PMs a single view across all active projects.

## What It Shows

**Pipeline (Kanban)** — 7 columns mapping to lifecycle phases. Each project is a card in its current phase.

| Column | Manifest Phases |
|--------|----------------|
| Intake | intake, vetting, spec_refinement |
| Approval | approval |
| Content | writing, editing |
| Automation | automation |
| Code & Security | code_security_review |
| Final Review | final_review |
| Ready | ready_for_publishing |

**Projects Table** — searchable list with phase progress bars, per-project refresh, edit, and delete.

**Project Detail** — expandable phase accordions showing completion dates, assignees, artifacts (linked to GitHub), module-level writing progress, and automation substeps.

## How It Works

1. A user registers a project by providing its GitHub repo URL
2. The dashboard fetches `publishing-house/manifest.yaml` via the GitHub API
3. Phase data is parsed and cached in PostgreSQL
4. A nightly job refreshes all projects; manual refresh is also available per project

The dashboard is **read-only** — all project state lives in the manifest. The dashboard never modifies it.

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

## Manifest Requirements

For a project to display correctly in the dashboard, its `publishing-house/manifest.yaml` must include:

```yaml
project:
  name: "Project Title"
  owner: "github-username"     # Required — shown in project detail
  type: "workshop"             # workshop or demo
  autonomy: "supervised"
  created: "2026-04-01"

lifecycle:
  phases:
    <phase_name>:
      status: "pending"        # pending | in_progress | completed | skipped
      completed_at: null       # ISO date when completed
      assignees: []            # GitHub usernames working on this phase
      artifacts: []            # File paths (linked to GitHub in the dashboard)
```

The `completed_at`, `assignees`, and `artifacts` fields drive what appears in the phase accordions. If they're missing, the accordion shows "None" for artifacts and no date.

## Deployment

Deployed to OpenShift using the same Ansible + Jinja2 pattern as RCARS:

```bash
# First-time setup
ansible-playbook ansible/deploy.yml -e env=dev -e kubeconfig=~/.kube/config --tags mgmt-rbac
ansible-playbook ansible/deploy.yml -e env=dev --tags update

# Subsequent deploys
ansible-playbook ansible/deploy.yml -e env=dev --tags builds
```

GitHub webhooks trigger automatic rebuilds on push.

## Repos

- [rhdp-publishing-house-dashboard](https://github.com/rhpds/rhdp-publishing-house-dashboard) — the dashboard app
- [rhdp-publishing-house](https://github.com/rhpds/rhdp-publishing-house) — the CLI skills and plugin
- [rhdp-publishing-house-template](https://github.com/rhpds/rhdp-publishing-house-template) — project template with manifest schema
