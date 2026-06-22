# Publishing House — Development Worklog

Session notes and handoff context for the PH dev team. Use this to communicate between developers what was done, what's in progress, and what the next person should pick up.

Clear periodically — the backlog ([BACKLOG.md](BACKLOG.md)) is the persistent roadmap.

---

## 2026-06-22 — Jira integration implementation, spec template, doc overhaul (Nate)

### Jira Integration (Central backend — fully implemented)
- **JiraClient** (`jira_client.py`): Sync HTTP client for Jira Cloud REST API v3, Basic auth, project key guardrail (`allowed_project_key` enforced on all write ops)
- **JiraTaskMapping** model + Alembic migration: maps manifest deliverables to Jira issues
- **JiraSyncService** (`jira_sync.py`): create_project (Epic + per-module Tasks with story points), sync_project (diff manifest vs Jira, transition tasks), get_open_initiatives, custody chain comments on Jira Epics
- **Gate integration**: Jira Epic+Tasks created at **approval gate** (not vetting — spec isn't stable until approved). Subsequent gates sync status. Non-blocking — Jira failures never block gate passes.
- **ph_get_open_initiatives** MCP tool: exposed for intake Initiative selection
- **ph_get_status** response now includes `jira` block with Epic URL, points completed/total
- **Periodic reconciliation**: hooks into APScheduler refresh to catch drift
- **Ansible deployment**: K8s Secret for Jira credentials, env vars conditional on `jira_url`
- Deployed to central-dev, tested end-to-end — 20 issues created in RHDPCD under Test Initiative (RHDPCD-2)
- Fixed Jira API URL: must use `api.atlassian.com/ex/jira/{cloudId}` not `redhat.atlassian.net` (site URL returns 404 for API tokens)
- Fixed RCARS SA allowlist: added `publishing-house-central-dev:default` to RCARS dev vars
- Fixed missing `spec_reviewer.py` and `llm.py` (uncommitted files broke MCP import chain)

### Design Decisions
- **Onboarded only**: Jira sync scoped to `rhdp_published` projects. Self-published and express excluded.
- **Approval gate creation**: Epic+Tasks created when spec is frozen, not at vetting (avoids churn during vetting ⇄ spec refinement loop)
- **Manifest opt-out**: `integrations.jira.enabled: false` disables Jira for testing. Not in template — undocumented developer option.
- **Initiative selection**: During intake, skill calls `ph_get_open_initiatives`, presents pick list. Source stored in `manifest.integrations.jira.initiative_key`.

### Intake Skill Updates
- **Design spec template** (`design-template.md`): Fixed section headings, bracketed placeholders. Intake fills in the template instead of generating freeform. Template also pushed to `rhdp-publishing-house-template`.
- **Jira issue as intake path** (Path C): New third entry — point at any Jira issue (any project) as requirements source. Uses Atlassian MCP tools. Source key stored in `project.source_issue`.
- **Spec validator rewritten**: Checks for exact template headings + unfilled placeholders instead of regex heading matching.

### Ansible Fixes
- **Build wait fix**: `oc wait` now targets the specific build name (from `oc start-build` output) instead of label selector. Fixes false negatives from pruned old builds.
- Added Tony, Sha, Prakhar API keys to central-dev MCP config

### Documentation Overhaul
- Renamed `portal.md` → `central.md`, `portal-deployment.md` → `central-deployment.md`
- Complete Portal → Central rename across all 15 active doc files
- Updated namespaces (`publishing-house-dev` → `publishing-house-central-dev`), repo names, deployment names
- Updated MCP tools table with Gate Service category (7 tools)
- Rewrote Central CLAUDE.md with current services, models, and tools
- Updated Jira integration overview status from "Proposed" to "Implemented"
- Jira spec updated: approval gate creation, enabled flag, Initiative selection, project key guardrail

### What's next
1. **Test full PH workflow end-to-end** with `ph-onboarded-ai` (reset to blank template with `jira.enabled: false`)
2. **Test Jira flow** with a fresh project that goes through approval gate — verify Epic+Tasks created correctly
3. **Service account provisioning** — still the production blocker for Jira
4. **Spec template conformance** — existing projects need their design.md aligned to the template

---

## 2026-06-22 — Gating overhaul, spec review, JIRA verification, infra requirements (Nate)

### JIRA Project (RHDPCD)
- Verified OJA-ITS-003 scheme switch is live — Initiative, Epic, Task all available
- Created RHDPCD-1 test ticket, walked through all 4 workflow states (New → Refinement → In Progress → Closed), confirmed global transitions
- Updated Jira integration spec with actual transition IDs, custom field IDs, Outcome type (level 3) for event grouping
- Updated prerequisites table — scheme switch and project creation marked complete, service account still pending

### Gating Overhaul (Central backend — 8 files)
- **Phase engine**: Self-published and express now have only `intake` as hard gate; everything else is soft
- **Gate service**: Soft gates auto-approve once prerequisites met — skip custody chain verification, self-approval checks, spec-change checks. Gate records still written for audit trail.
- **Vetting**: RCARS still runs for soft gates. If RCARS unavailable, soft gates complete anyway (informational). Hard gates still block.
- 7 new soft gate tests, all 56 related tests passing

### Spec Review (2 new services)
- **`llm.py`**: LLM provider routing following RCARS pattern — LiteMaaS preferred → Vertex AI fallback → Anthropic API fallback
- **`spec_reviewer.py`**: LLM-powered spec review — summarizes project, assesses quality/infrastructure/actionability, recommends approve/needs_work/reject
- Integrated at approval gate: hard gates can reject on "reject" recommendation; soft gates record findings only
- Graceful degradation if no LLM provider configured

### Infrastructure Requirements (intake + validation)
- Added `## Infrastructure Requirements` to spec validator required sections
- Updated intake skill with infrastructure fields aligned to existing catalog intake form (base CI, sizing, cloud provider, automation approach, workloads)
- Updated spec guidelines reference with detailed infrastructure section

### Ansible / Deployment
- Added LiteMaaS + Vertex AI credentials to `central-dev.yml`
- Created K8s secrets for LiteMaaS API key and Vertex credentials in infra template
- Wired LLM env vars into backend deployment with Vertex volume mount
- Deployed PH Central dev with full `--tags deploy`

### What's next
1. **Push PH Central code changes** — commit and push to feature branch, rebuild
2. **Test spec reviewer end-to-end** — run approval gate with LLM credentials live
3. **Jira sync implementation** — service account is the remaining blocker

---

## 2026-06-19 — Dashboard redesign for PH Central (Nate)

### Design
- Brainstormed and designed the dashboard redesign for PH Central
- Design spec: [2026-06-19-dashboard-redesign-for-central.md](docs/superpowers/specs/2026-06-19-dashboard-redesign-for-central.md)
- Implementation plan: [2026-06-19-dashboard-redesign-for-central.md](docs/superpowers/plans/2026-06-19-dashboard-redesign-for-central.md)
- Key decisions: keep PatternFly 6 (Red Hat standard), 6-column kanban with merged iterative/parallel columns, cache phase statuses in DB for instant board load, gate history inline per phase (not a separate tab)

### Backend (4 commits + 2 fixes)
- Added 5 cached status fields to Project model (`cached_phase_statuses`, `cached_current_phase`, `cached_next_action`, `cached_manifest_data`, `cached_at`) + Alembic migration
- Rewrote `app/api/projects.py`: 9 REST endpoints using GitRepoReader + PhaseEngine + GateService instead of old Manifest/Phase models
- Rewrote `app/services/refresh.py`: periodic sync now caches phase statuses via PhaseEngine
- New Pydantic schemas: `CentralProjectCreate`, `CentralProjectResponse`, `GateRecordResponse`, `ProjectStatusResponse`
- Fixed MCP `ph_register` to populate cached status on registration (was returning empty overview)
- Added `app/core/logging.py`: consistent timestamped JSON logging across all MCP tools, REST endpoints, gate decisions, and refresh cycles
- Deleted superseded test files (`test_api_projects.py`, `test_refresh.py`), 123 tests passing

### Frontend (rewrite in place)
- New TypeScript types: `CentralProject`, `GateRecord`, `ProjectStatus` with data-driven `PIPELINE_COLUMNS` config
- Pipeline board: 6-column kanban — Intake, Vetting/Spec (ITERATIVE), Approval, Writing+Automation (PARALLEL), Review, Ready
- Project detail: phase progress bar, phase accordions with gate history drill-down, artifacts per phase, Next Action card, branch shown in header
- Projects list: branch column, deployment mode, current phase, progress bar from cached statuses
- Register page: added branch field (defaults to `main`)
- Masthead: "Publishing House Central", subtitle removed
- Timestamps include time, not just date
- Deleted `RefreshButton.tsx` (inlined), Next.js build passes clean

### Deployment
- All on `feature/ph-central-registration` branch in `rhdp-publishing-house-central`
- Deployed to `publishing-house-central-dev` namespace: migration + backend + frontend builds
- Env is `central-dev` (not `dev`), kubeconfig at `~/devel/secrets/ph-central-mgmt-central-dev.kubeconfig`

### What's next
1. **Test the full flow** — register via orchestrator, verify dashboard shows correct data, test refresh
2. **SpecValidator LLM quality checks** — backend LLM via LiteLLM/MaaS
3. **Deterministic client layer** — still the blocking item for reliable orchestrator behavior
4. **Merge feature branches** — after validation

---

## 2026-06-18/19 — Publishing House Central architecture + implementation (Nate)

### Backlog triage and quick wins
- Triaged the full PH backlog, prioritized near-term items
- Added Zero-Touch Showroom support to the project template (`runtime/`, `setup/` dirs), manifest (`showroom_type` field), intake skill, and orchestrator (cleanup for classic projects)
- Dropped `ph_store_validation_results` wiring — git review files are the source of truth, portal UI adds complexity without current value
- Updated Jira integration spec: project key RHDPCD, Template 2 (Basic Project) with self-service switch to OJA-ITS-003 (Standard) via Delegated Project Admin. JSM request submitted.

### PH Central architecture evolution (major)
- Brainstormed and designed the architecture evolution from portal to "Publishing House Central"
- Design spec: [2026-06-19-publishing-house-central-design.md](docs/superpowers/specs/2026-06-19-publishing-house-central-design.md)
- Core principle: **trust but verify** — local LLM and skills have full creative freedom, Central owns validation, gate enforcement, and custody chain
- All phases are required (no optional phases), three deployment mode profiles with different gate hardness
- Central reads from git (not MCP payloads), project identity = repo URL + branch
- Custody chain: independent record of gate decisions that the manifest can't override

### PH Central backend implementation (63 tests)
- Renamed repo from `rhdp-publishing-house-portal` to `rhdp-publishing-house-central`
- All work on `feature/ph-central-registration` branch (not merged to main)
- **New services:** GitRepoReader, PhaseEngine, GateService, SpecValidator
- **New models:** GateRecord (custody chain), SubmittedResult, Project.branch column
- **7 MCP tools:** `ph_register`, `ph_list_projects`, `ph_get_status`, `ph_request_gate`, `ph_submit_results`, `ph_get_history`, `ph_approve` (noted, deferred)
- **Gate enforcement:** Central verifies its own gate records (doesn't trust manifest), RCARS unavailable = hard reject, self-approval rejected for onboarded projects, spec commit tracking for vetting loop
- **Vetting posture:** Server-side challenging assessment with fixed tone, "completed" not "approved" for non-approval phases
- Deployed to `publishing-house-central-dev` namespace on ocpv-infra01, parallel to existing dev deployment
- RCARS SA allowlist updated for new namespace
- Fixed Ansible build tasks (replaced `kubernetes.core.k8s_info` with `oc` commands for Build resources)

### Skill updates
- All work on `feature/ph-central-skills` branch (not merged to main)
- Orchestrator: uses Central tools, tool boundary enforcement, one-gate-per-request rule, all phases required
- Intake: removed direct RCARS calls, vetting handled by Central via orchestrator, spec refinement reads vetting findings for recommendations

### MCP server configuration
- Found and fixed MCP config location: `~/.claude.json` (not `~/.claude/mcp.json` or `~/.claude/settings.json`)
- Transport type `http` with trailing slash matches existing working servers
- Moved MCP config to `~/devel/secrets/ph-mcp-dev.json`, removed old `~/.config/rhdp-publishing-house/` directory
- Updated user docs three times as we found the correct configuration

### Key discovery: LLM presentation problem
- Despite server-side gate enforcement working correctly, the LLM orchestrator consistently reinterprets Central's output — says "approved" when Central said "completed", ignores `vetting_assessment` fields, auto-advances through multiple gates
- Multiple rounds of instruction strengthening (one-gate-per-request, STOP/WAIT, verbatim presentation) did not reliably fix the behavior
- This is a fundamental limitation of LLM-driven interfaces for workflow enforcement, not fixable with better instructions
- Added **deterministic client layer** as BLOCKING priority backlog item

### Other fixes
- Removed stale `rhdp-skills-marketplace` local dev clone (was causing confusion with outdated v2.4.8 vs installed v2.14.0)
- Saved memory: always check installed plugin paths (`~/.claude/plugins/marketplaces/`) not dev clones

### Feature branches (NOT merged to main)
| Repo | Branch | Content |
|---|---|---|
| `rhdp-publishing-house-central` | `feature/ph-central-registration` | Backend: 7 MCP tools, 5 services, 3 models, 63 tests, Ansible fixes |
| `rhdp-publishing-house-skills` | `feature/ph-central-skills` | Orchestrator + intake rewritten for Central |
| `rhdp-publishing-house` | `feature/ph-central` | Spec, plans, backlog, submodule pointer |

### What's next
1. **Deterministic client layer** (BLOCKING) — design the application that sits between user and Central, controls workflow deterministically, uses LLM only for creative work
2. ~~**Dashboard redesign**~~ — DONE (see 2026-06-19 session above)
3. **SpecValidator LLM quality checks** — backend LLM via LiteLLM/MaaS for spec quality assessment
4. **Merge feature branches** — after the client layer approach is decided and validated

---

## 2026-05-15 — Phase 4 brainstorm + design spec (Nate)

### Hosted Workspace design (formerly "Portal Chatbot")
- Brainstormed and designed the Phase 4 hosted access solution
- Original concept was a portal chatbot calling MCP tools — evolved to a full hosted Dev Spaces workspace after determining full CC skill parity was required
- Key architectural decisions:
  - OpenShift Dev Spaces with custom UDI (RHEL9 base), hosted on `quay.io/rhpds/ph-udi:latest`
  - Portal provisions workspaces via Dev Spaces API, MaaS keys via LiteLLM REST API
  - One workspace per project per user, opt-in ("Open in Dev Spaces" button on project detail)
  - One-way integration only: workspace → portal (MCP), portal never pushes to workspace
  - CC CLI updated at every session start, not baked into image
  - MaaS key lifecycle fully portal-managed — provision, validate on resume, revoke on delete
  - Key duration configurable (env var), expired key = restart workspace from portal
  - Chose Dev Spaces over lighter alternatives partly for Red Hat dog-fooding story
- Design spec written: [2026-05-15-hosted-workspace-design.md](docs/superpowers/specs/2026-05-15-hosted-workspace-design.md)
- BACKLOG.md updated: Phase 4 renamed and marked SPEC COMPLETE, new backlog items added

### Backlog additions
- MCP auth rationalization (near-term)
- Lightweight express mode execution (future — Dev Spaces too heavy for one-off demos)
- UDI image rebuild pipeline, mid-session key rotation, Dev Spaces API exploration (future)

### What's next
- **Phase 4 spec review** — share with team for feedback before implementation planning
- **Phase 3: Jira integration** — spec done, blocked on Jira SA provisioning
- **Express skill** — unblocked, needs brainstorm
- See [BACKLOG.md](BACKLOG.md) for full roadmap

---

## 2026-05-06 — Documentation overhaul + template restructuring (Nate, pre-PTO)

### Documentation accuracy review
- Cross-referenced all docs/ against actual code in all 4 repos (portal, skills, template, main)
- Fixed 12 files: broken links, wrong parameter types, missing MCP tools, stale branch refs
- Replaced 7 ASCII art diagrams with Mermaid (exec summary, how-it-works, portal, rcars-integration, portal-deployment)
- Added Mermaid custom_fences config to mkdocs.yml
- Updated CLAUDE.md MCP tools table: added 3 missing tools (`ph_get_launch_instructions`, `ph_store_validation_results`, `ph_get_validation_results`)
- Fixed `ph_get_launch_instructions` param type (int → str), advisor poll interval (3s → 10s), `ph_list_projects` return shape
- Removed stale `gsd-project` branch references from portal-deployment.md

### Portal cleanup
- Renamed `_ph_dashboard_oauth` cookie → `_ph_portal_oauth`
- Fixed "from the dashboard" → "from the portal" in delete dialog
- Built and deployed frontend to dev

### Template restructuring
- Embedded Showroom scaffold in PH template (site.yml, ui-config.yml, content/antora.yml, nav.adoc, index.adoc)
- Removed submodule pattern: content/ and automation/ are now regular directories, not separate repos
- Removed `integrations.showroom_repo` and `integrations.automation_repo` from manifest template
- Removed 84 lines of submodule gate logic from orchestrator SKILL.md
- Updated template CLAUDE.md, README.md, .gitignore
- Updated how-it-works.md project template section

### Housekeeping
- Removed `.planning/` directory (replaced by backlog + docs as source of truth)
- Added `.claude/` to .gitignore, restored `.superpowers/`

### Test prompts
- Created 15 intake test prompts in test/ (3 modes × 5 tech areas)
- Mix of direct asks and CFP abstract styles for realistic intake testing

### What's next
- **Test intake end-to-end** using the test prompts against live MCP server
- **Phase 3: Jira integration** — spec done, ready for implementation planning (blocked on Jira SA)
- **Phase 4: Portal chatbot** — needs brainstorm
- **Express skill** — unblocked, needs design
- See [BACKLOG.md](BACKLOG.md) for full roadmap
