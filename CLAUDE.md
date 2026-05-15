# RHDP Publishing House

AI-powered content lifecycle management for Red Hat Demo Platform. One command (`/rhdp-publishing-house`) provides a persistent, state-aware orchestrator that manages the entire content lifecycle — intake, writing, editing, automation, review, publishing — through specialized Claude Code agent skills.

Content developers become content architects: design the architecture, agents handle the writing, editing, automation, and review.

## Repository Structure

Four repos, one project. This repo (`rhdp-publishing-house`) is the central hub for development, planning, and documentation. It contains two submodules that point to published repos.

```
rhdp-publishing-house/              ← YOU ARE HERE (dev + planning + docs)
├── skills-plugin/                  ← submodule → rhdp-publishing-house-skills
├── template/                       ← submodule → rhdp-publishing-house-template
├── docs/                           ← all project documentation
├── BACKLOG.md                      ← roadmap and work queue
├── WORKLOG.md                      ← session handoff notes between developers
└── CLAUDE.md                       ← this file

rhdp-publishing-house-portal/       ← separate repo (portal + MCP server + API)
rhdp-publishing-house-skills/       ← published skills (users clone this)
rhdp-publishing-house-template/     ← project template (users clone to start a project)
```

All repos live under `github.com/rhpds/`. Clone with SSH.

### What Each Repo Does

**rhdp-publishing-house** (this repo): Development hub. Skills are developed here via the `skills-plugin` submodule, then pushed to the skills repo. Documentation, specs, plans, and the backlog all live here. A developer working on PH features works here. Regular PH users never need this repo.

**rhdp-publishing-house-portal**: FastAPI backend + Next.js frontend deployed on OpenShift. Houses the MCP server (mounted at `/mcp`), REST API, database models, RCARS client, and all backend services. The portal is also the single gateway for Jira sync (planned). Code repo only — regular users never interact with it directly.

**rhdp-publishing-house-skills**: Published skills for Claude Code / Cursor. Users install PH by cloning this repo and pointing their AI tool at it. Contains the orchestrator, intake, writer, editor, automation, and worklog skills. During development, changes flow through the submodule in this repo.

**rhdp-publishing-house-template**: Cloned by users to start a new PH project. Contains the manifest template (`publishing-house/manifest.yaml`), content directory (mirrors Showroom structure), and automation directory. The content portion should stay synced with the upstream Showroom notebook template.

### Submodule Workflow

When developing skills or template changes:
1. Edit in the submodule directory (`skills-plugin/` or `template/`)
2. Commit and push within the submodule (pushes to the published repo)
3. Commit the submodule pointer update in this repo
4. Pull the local clone if you have one (e.g., `~/devel/publishing-house/rhdp-publishing-house-skills`)

## Architecture

### Source of Truth

The git manifest (`publishing-house/manifest.yaml`) is the source of truth for project state in onboarded and self-published modes. Express mode projects (transient, no git repo) use the portal database. Jira is a one-directional sync target — PH pushes to Jira, Jira never drives PH state.

### Portal Backend (Single Gateway)

The portal backend IS the MCP gateway. FastMCP 3.2+ server mounted at `/mcp` on the FastAPI app. One codebase, one deployment, one database. Every external service gets a client class in `app/services/` with retry logic and structured errors. MCP tools delegate to these clients — they never make HTTP calls directly.

```
rhdp-publishing-house-portal/src/backend/
├── app/
│   ├── main.py              # FastAPI app + FastMCP mount
│   ├── core/
│   │   ├── config.py        # Settings (env vars, secrets)
│   │   ├── database.py      # SQLAlchemy session factory
│   │   └── types.py         # Shared types (JSONBType)
│   ├── mcp/
│   │   ├── server.py        # FastMCP server instance
│   │   ├── auth.py          # API key auth middleware (SHA-256, hmac.compare_digest)
│   │   ├── tools.py         # Project/manifest MCP tools
│   │   ├── rcars_tools.py   # RCARS query/catalog MCP tools
│   │   └── session_tools.py # Session continuity + express MCP tools
│   ├── services/
│   │   ├── rcars_client.py  # RCARS v2 API client (SA token auth, async)
│   │   ├── github_client.py # GitHub API client
│   │   └── manifest_parser.py
│   ├── models/              # SQLAlchemy ORM (Project, Manifest, Phase, IntakeSession, ExpressMetric)
│   ├── schemas/             # Pydantic request/response schemas
│   └── api/                 # REST API routes (projects, health, validations)
├── alembic/                 # Database migrations
├── tests/                   # pytest test suite
└── requirements.txt
```

### MCP Tools Available

| Tool | Purpose |
|------|---------|
| `ph_list_projects` | List projects (with optional owner_email filter) |
| `ph_get_launch_instructions` | Get step-by-step ordering instructions for a project |
| `ph_store_validation_results` | Store validation results from agnosticv:validator or showroom:verify-content |
| `ph_get_validation_results` | Retrieve stored validation results (optional phase filter) |
| `ph_rcars_query` | Submit RCARS advisor query, poll until complete |
| `ph_rcars_catalog_search` | Search RCARS catalog items |
| `ph_rcars_catalog_item` | Get full metadata for a specific catalog item |
| `ph_store_intake_results` | Store intake data in portal DB |
| `ph_get_intake_results` | Retrieve stored intake data |
| `ph_list_intake_sessions` | List intake sessions by owner |
| `ph_sync_manifest` | Sync manifest content to portal DB |
| `ph_record_express_run` | Record express mode run metrics |

### Auth Model

- **External MCP access** (Claude Code users): Bearer API key in Authorization header. Keys stored as SHA-256 hashes in K8s Secret `ph-mcp-api-keys`. Validated via FastMCP Middleware.
- **Cluster-internal RCARS calls**: ServiceAccount token, auto-mounted, validated via K8s TokenReview API. SA added to RCARS allowlist.
- **Portal UI**: OpenShift OAuth proxy (existing).
- **No OAuth for MCP** this milestone — overkill for <20 internal users.

### Skills

Six skills in `skills-plugin/skills/`:

| Skill | Purpose |
|-------|---------|
| `orchestrator` | Entry point. Discovers projects, reads manifest, dispatches to other skills, manages phase transitions. MCP-aware: checks local manifest → portal fallback → new intake. |
| `intake` | Conversational project intake. Two entry paths ("I have a spec" / "I have an idea"). Deployment mode selection (onboarded, self-published, express). RCARS vetting. Session continuity via MCP. |
| `writer` | Content writing agent. Wraps `showroom:create-lab` and `showroom:create-demo`. Works per-module from spec outlines. |
| `editor` | Content review agent. Wraps `showroom:verify-content`. |
| `automation` | Automation agent with sub-phases: requirements (7a), catalog item (7b), automation code (7c), testing (7d). |
| `worklog` | Session bridging. Records what was done, what's next. |

### Deployment Modes

| Mode | Git Repo? | State Location | Jira Tracked? |
|------|-----------|----------------|---------------|
| `rhdp_published` (onboarded) | Yes | Git manifest | Yes |
| `self_published` | Yes | Git manifest | Yes |
| `express` | No | Portal DB only | No (transient) |

### Manifest Lifecycle Phases

```
intake → vetting → spec_refinement → approval → writing → editing →
automation → code_security_review → final_review → ready_for_publishing
```

Required phases: intake, writing, code_security_review, final_review. Optional phases can be skipped. The orchestrator manages transitions; individual skills must not touch phase-level state.

### Infrastructure

- **Cluster**: OpenShift (`ocpv-infra01.dal12.infra.demo.redhat.com`)
- **Namespaces**: `publishing-house-dev` (portal), `rcars-dev` (RCARS)
- **Database**: PostgreSQL 16 (deployed as StatefulSet)
- **Deployments**: Ansible manages everything — `ansible-playbook ansible/deploy.yml -e env=dev --tags deploy`
- **Build tags**: `build-backend`, `build-frontend`, `builds` (both), `deploy` (full), `apply` (manifests only), `migrate` (Alembic only)

## Current State (as of 2026-05-06)

### What's Built and Working
- Orchestrator with MCP-aware project discovery and phase dispatch
- Intake with 3-mode routing (onboarded, self-published, express)
- Writer, editor, automation agents (functional, improving)
- Portal backend: FastAPI + MCP server + RCARS client + session tools
- Portal frontend: Next.js + PatternFly 6 (kanban, project table, phase detail)
- RCARS integration: 3 MCP tools, SA token auth, cross-namespace connectivity
- Express mode framework: DB models, session tools, intake routing (express skill itself is backlogged)
- API key auth for MCP endpoint
- Ansible deployer with per-component build tags

### What's Next (see BACKLOG.md)
- **Phase 3: Jira Integration** — spec complete, ready for implementation planning
- **Phase 4: Portal Chatbot** — needs brainstorm
- **Express skill** — unblocked, needs own brainstorm+spec

### Known Blockers
- Jira service account on redhat.atlassian.net — gating dependency for Phase 3 deployment
- Anthropic SDK issue #1020 (Vertex AI streaming+tools) — affects Phase 4 chatbot

## Development Guidelines

### Key Rules
- **Manifest is truth.** All project state flows from `publishing-house/manifest.yaml`. Portal and Jira are downstream consumers.
- **Ansible deploys everything.** No manual `oc edit`. Secrets, routes, config — all through Ansible.
- **One gateway.** Portal backend is the single MCP gateway. Chatbot, Jira sync, and CC users all flow through the same tool functions.
- **Skills don't own phase transitions.** The orchestrator manages `current_phase` and phase statuses. Skills read their inputs from the manifest and update their own artifacts.
- **Every push triggers a build.** Commits pushed to the portal repo trigger OpenShift builds. Batch commits and push at meaningful milestones.
- **SA token re-read per request.** Never cache the K8s SA token — it rotates after 1 hour on OCP 4.11+.
- **`yaml.safe_load` always.** Never use `yaml.load` for manifest parsing.

### Making Changes

**Adding a new MCP tool:**
1. Create the tool function in `app/mcp/` (e.g., `rcars_tools.py`)
2. Use `@mcp.tool()` decorator from `app.mcp.server`
3. Import the module in `app/main.py` (side-effect import registers the tool)
4. If it calls an external service, create/use a client in `app/services/`
5. Write tests in `tests/`
6. The chatbot (Phase 4) will automatically inherit the tool via programmatic tool definition extraction

**Adding a new skill:**
1. Create directory under `skills-plugin/skills/<name>/`
2. Add `SKILL.md` with frontmatter (`name`, `description`, `model`)
3. Skill reads from manifest, does its work, updates its artifacts
4. Skill must NOT modify `lifecycle.current_phase` or other phase statuses
5. Add routing entry to orchestrator's `SKILL.md`

**Deploying changes:**
```bash
cd rhdp-publishing-house-portal

# Config/secret changes only (API keys, env vars, route config)
ansible-playbook ansible/deploy.yml -e env=dev --tags apply

# Backend code changes only
ansible-playbook ansible/deploy.yml -e env=dev --tags build-backend

# Frontend code changes only
ansible-playbook ansible/deploy.yml -e env=dev --tags build-frontend

# Full deploy (infra + app + builds + migrations) — first deploy or major changes
ansible-playbook ansible/deploy.yml -e env=dev --tags deploy

# Just run migrations
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

### Testing
```bash
cd rhdp-publishing-house-portal/src/backend
python -m pytest tests/ -x -q --timeout=30    # quick run
python -m pytest tests/ -v --timeout=60       # full suite
```

## Documentation

Docs live in `docs/` with this structure:

| Directory | Content |
|-----------|---------|
| `docs/` (root) | Overview docs: index, executive-summary, how-it-works, getting-started |
| `docs/architecture/` | System design: portal, RCARS integration, express mode, Jira integration |
| `docs/admin/` | Operational: portal deployment, MCP auth, RCARS service auth, common rules |
| `docs/user/` | End-user guides: Claude Code setup |
| `docs/api/` | API reference: MCP tools |
| `docs/superpowers/specs/` | Historical design specs from brainstorming sessions |
| `docs/superpowers/plans/` | Historical implementation plans |

## Design Specs

Design decisions are documented in `docs/superpowers/specs/`. Read the relevant spec before working on a feature:

| Spec | Covers |
|------|--------|
| `2026-04-09-rhdp-publishing-house-design.md` | Original PH design (orchestrator, agents, manifest) |
| `2026-04-20-skills-redesign.md` | Deployment modes, worklog, smart intake, phase ordering |
| `2026-04-27-rcars-integration-design.md` | RCARS MCP gateway, API key auth, SA token auth |
| `2026-04-28-express-mode-design.md` | Express mode lifecycle, RCARS base-finding, portal DB state |
| `2026-05-05-jira-integration-design.md` | Jira sync, points model, ticket hierarchy, sync triggers |
