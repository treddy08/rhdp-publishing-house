# Publishing House — Backlog & Roadmap

Development roadmap for the RHDP Publishing House. Organized by milestone and priority. This is both the planning document and the work queue.

---

## Milestone 2: Superpowers (Current)

Portal as MCP gateway, express mode, Jira visibility, hosted chatbot. MCP gateway is the foundation — every subsequent feature consumes its tools.

### Completed

| Phase | What Shipped | Date |
|---|---|---|
| Phase 1: RCARS MCP Gateway | Portal as single MCP gateway, API key auth (FastMCP Middleware), SA token auth for cluster-internal RCARS, 3 RCARS tools (`ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`), health endpoint, Ansible infrastructure (Route, Secret, volume mount), intake vetting migrated from curl to MCP tool, 5 documentation deliverables. 7 plans, all verified. | 2026-05-01 |
| Phase 2: Express Mode Framework | DB models (IntakeSession, ExpressMetric, JSONBType DRY), 5 session MCP tools, orchestrator MCP-aware startup with portal fallback, intake three-mode routing with express dead-end at environment gate, manifest sync, graceful MCP degradation. 4 plans, all verified. Human UAT pending for live MCP server tests. | 2026-05-04 |

### Phase 3: Jira Integration — NEXT

**Goal:** Stakeholders can follow project progress in Jira without leaving their existing workflow.

**Status:** Brainstorm complete. Design spec written ([2026-05-05-jira-integration-design.md](docs/superpowers/specs/2026-05-05-jira-integration-design.md)). Ready for implementation planning.

**Key decisions made:**
- Dedicated Jira project (RHDPPH, name TBD) — can't modify GPTEINFRA schema
- Three-level hierarchy: Initiative (effort) → Epic (project) → Task (deliverable)
- Fixed points per deliverable type, auto-created by Portal
- One-directional sync: PH → Jira always, Jira → PH never (v1)
- Only the Portal backend talks to Jira — no LLM in the sync loop
- Sync triggers: MCP-triggered (real-time), polling (15-30 min), manual refresh
- Jira Cloud, REST API v3, service account with API token

**Prerequisites (blocking deployment):**
- [ ] RHDPCD Jira project created (JSM request submitted 2026-06-18, waiting on PME)
- [ ] Switch to OJA-ITS-003 (Standard) issue type scheme via Delegated Project Admin (self-service, after project creation)
- [ ] Jira service account provisioned on redhat.atlassian.net

**Requirements:** JIRA-01 through JIRA-06

### Phase 4: Hosted Workspace (Dev Spaces) — SPEC COMPLETE

**Goal:** Users without local Claude Code get full PH skill parity through a hosted Dev Spaces workspace launched from the portal.

**Status:** Brainstorm complete. Design spec written ([2026-05-15-hosted-workspace-design.md](docs/superpowers/specs/2026-05-15-hosted-workspace-design.md)). Ready for team review and implementation planning.

**Architecture decided:**
- OpenShift Dev Spaces with custom UDI (CC CLI, extension, PH skills, oc, Ansible)
- Portal provisions workspaces via Dev Spaces API + MaaS keys via LiteLLM API
- One workspace per project per user, opt-in (subtle "Open in Dev Spaces" button on project detail)
- One-way integration: workspace → portal (MCP), portal never pushes to workspace
- CC CLI updated at session start (not baked into image)
- Git is the sync mechanism — pull on resume, push on commit
- Base image: `registry.redhat.io/devspaces/udi-rhel9`, hosted on `quay.io/rhpds/ph-udi:latest`
- Target audience: content developers first, broader audience later

**Backend additions:**
- `WorkspaceManager` service (create, resume, delete, status)
- `LiteLLMClient` service (provision, validate, revoke, extend keys)
- `DevSpacesClient` service (create, start, stop, delete workspaces)
- `Workspace` DB model (project_id, user_id, workspace_id, workspace_url, maas_key_alias, maas_key_id)
- 4 new API routes under `/api/v1/projects/{id}/workspace`

**MaaS key lifecycle:**
- Provisioned at workspace creation via LiteLLM REST API (`POST /key/generate`)
- Key duration configurable (env var, default TBD — 7d or 30d)
- Validated on workspace resume — if expired, portal auto-provisions new key
- Revoked on workspace deletion
- User never sees or manages keys

**Dog-fooding:** Chose Dev Spaces over lighter alternatives (web terminal, chat UI) partly for the Red Hat product dog-fooding story

**Prerequisites:**
- [ ] Dev Spaces operator installed on ocpv-infra01
- [ ] LiteLLM endpoint accessible from portal namespace
- [ ] Custom UDI image built and pushed to quay.io/rhpds
- [ ] Dev Spaces API auth (service account or OAuth) configured

---

## Near-Term (Post-Milestone 2)

Items that are unblocked or nearly unblocked. Not on the current roadmap but high value.

### Deterministic client layer — PRIORITY (BLOCKING)

**Origin:** PH Central testing (2026-06-19). Multiple rounds of testing showed that LLM-driven skill instructions cannot reliably control presentation or enforce workflow discipline, regardless of how explicit the instructions are.

**Problem.** The PH Central backend works — gates enforce correctly, RCARS vetting runs, custody chain records decisions, self-approval is rejected. But the client layer (Claude Code orchestrator skill) rewrites server output, uses the word "approved" when Central said "completed", ignores `vetting_assessment` fields, auto-advances through multiple gates on a single "proceed," and searches wherever it feels like despite explicit instructions. Stronger instructions haven't fixed this — it's a fundamental limitation of LLM-driven interfaces for workflow enforcement.

**The pattern:** Every time we fix the LLM behavior with instructions, it works for one test and breaks the next. The server-side move solved the logic problem but not the presentation problem. The LLM owns the output and reinterprets everything.

**Proposed approach:** A lightweight TypeScript (or Python) CLI application that sits between the user and Central. The user still has a conversational experience, but the application controls:
- What Central tools are called and in what order (deterministic, not LLM-decided)
- How gate results are presented (formatted from Central's response, not reinterpreted)
- When to stop and wait for user input (code-enforced checkpoints, not LLM instructions)
- Which phases allow LLM involvement (creative work like spec writing, content generation) vs which are app-controlled (gates, vetting presentation, phase transitions)

The LLM is still used for creative work — intake conversation, spec generation, content writing. But the workflow orchestration, gate presentation, and phase management are handled by the application, not the LLM.

**Architecture options to evaluate:**
1. **CLI app that shells out to Claude/LLM for creative phases** — the app drives the workflow, calls Central's MCP tools directly, formats output, and only invokes an LLM when creative input is needed (intake conversation, spec refinement suggestions, content writing)
2. **Claude Code extension/hook that intercepts tool calls** — use Claude Code hooks to enforce which tools can be called and format responses before the LLM sees them
3. **Web-based workflow UI in Central dashboard** — forms-driven workflow with embedded LLM chat for creative phases, no free-form LLM orchestration

**What this replaces:** The `rhdp-publishing-house` orchestrator and intake SKILL.md files become secondary — available for power users who want the raw Claude Code experience, but not the primary interface for most users.

**Depends on:** PH Central backend (deployed and tested). The backend is ready — this is about what sits in front of it.

**Why blocking:** Every other backlog item (dashboard redesign, Jira integration, Showroom skill updates) builds on the assumption that the client layer works reliably. If the client can't be trusted to present results faithfully or follow workflow rules, the features built on top of it inherit that unreliability.

### Dashboard redesign for PH Central — PRIORITY

**Origin:** PH Central architecture evolution (2026-06-19). Feature branch deployed and running.

**Problem.** The dashboard was built for the portal model — it reads from the `Manifest` model which was populated by `ph_sync_manifest` pushes from the client. With PH Central, manifests are read from git by the backend, not pushed via MCP. The dashboard shows empty project cards because nothing populates the old model.

**What needs to change:**

1. **Data source** — The dashboard should read project status from the `ProjectRegistration` model (new) and compute phase status via `PhaseEngine` or a REST endpoint that wraps `ph_get_status`. It should NOT depend on `Manifest.parsed_data` being populated by MCP sync.

2. **Pipeline view** — The kanban columns should match the Central phase profiles. All phases are required (no optional phases). The vetting ⇄ spec refinement loop and writing ↔ automation concurrency should be visually represented.

3. **Custody chain visibility** — Each project card should show gate history from `GateRecord`. Managers need to see: which gates passed, who approved, whether any gates were overridden, and RCARS vetting findings.

4. **Registration view** — The "Register" nav item should show the manual registration form (repo URL + branch) and list all registered projects with their sync status.

5. **Project detail** — Clicking a project should show: manifest metadata (read from git via backend), phase status with gate history, submitted results from local skills, and links to the repo.

6. **Naming** — Update "RHDP Publishing House" / "Content Lifecycle Portal" to "Publishing House Central" throughout the frontend.

**Technical notes:**
- Frontend: Next.js 15 + PatternFly 6 (existing stack)
- New REST endpoints needed: `GET /api/v1/central/projects` (wraps ProjectRegistration), `GET /api/v1/central/projects/{id}/gates` (wraps GateRecord), `GET /api/v1/central/projects/{id}/status` (calls PhaseEngine against git manifest)
- The old REST endpoints (`/api/v1/projects`) can remain for backward compatibility during transition
- The frontend lives in `rhdp-publishing-house-central/src/frontend/`

**Depends on:** PH Central backend (deployed on `feature/ph-central-registration` branch). Feature branch must be merged or the dashboard work done on the same branch.

**Scope:** Frontend redesign + 2-3 new REST endpoints. No backend service changes — PhaseEngine, GateService, and GitRepoReader are already built.

### SpecValidator LLM quality checks — PRIORITY

**Origin:** PH Central testing (2026-06-19). SpecValidator structural checks are deployed but quality assessment requires a backend LLM call.

**Problem.** The structural validator checks that required sections exist (learning objectives, products, audience, duration, modules) but cannot assess quality. During testing, the intake skill generated vague learning objectives like "Interact with a foundation model..." that passed structural validation but were refined to better versions during spec refinement. A quality validator would catch these before the spec leaves intake.

**What's needed:**
- Backend LLM call via LiteLLM/MaaS with a fixed, challenging prompt
- Checks: Are objectives specific and testable? Are module descriptions detailed enough for a writer agent? Does the scope match the stated duration? Are products named correctly per Red Hat standards?
- The prompt must be pessimistic — it's a quality gate, not encouragement
- Results are advisory during spec refinement, blocking at the approval gate
- Same LiteLLM/MaaS integration pattern already used in RCARS

**Depends on:** LiteLLM/MaaS endpoint accessible from the `publishing-house-central-dev` namespace. Same configuration as RCARS uses.

**Scope:** One new method in `SpecValidator`, LiteLLM client setup, wire into `ph_request_gate` for approval phase.

### Showroom skills — orchestrator + parallel subagent refactor

**Origin:** Prakhar Srivastava proposal (2026-05-19). Reviewed and approved 2026-06-16.

**Problem.** `verify-content` and `create-lab` both run sequentially in a single Claude context. On a 6-module lab, `verify-content` makes 5 passes across all files one after the other (~8 min wall time). `create-lab` is 13 sequential steps. Since PH's writer and editor agents wrap these skills, this slowness flows directly into the writing and editing phases.

**How this differs from the original "subagent-per-module" idea.** The original Future Milestone item was narrow: "run each module's review in its own agent instead of sequentially." Pure parallelism, same logic. This proposal adds three things on top that make it actually work:

1. **Pre-flight orchestrator stage** — before any agents run, extract cross-module context (nav order, defined Antora attributes, first-use acronym map) into a `shared_context` JSON. Without this, module 4's agent has no way to know AAP was already expanded in module 1. The original idea had no answer for cross-module dependencies.
2. **Structured output contract** — every agent returns findings in a fixed JSON schema with a `Critical|High|Warning|Info` severity enum. The original idea said "parallel agents" with no spec for how results merge. This makes dedup and cross-module logic possible in a merge stage.
3. **Applies to `create-lab` too**, not just `verify-content`. Original idea was review-only. This extends it to generation — all intake questions upfront, then parallel file creation (index, overview, details, first module simultaneously). Continue mode stays sequential since story continuity requires reading previous modules.

**Proposed pipeline for `verify-content`:**

| Stage | Who | What |
|---|---|---|
| Pre-flight | Orchestrator (sequential) | Reads nav.adoc for module order, antora.yml for defined attributes, scans all .adoc for first-use acronym map. Outputs `shared_context` JSON. |
| Scaffold check | 1 agent | site.yml, ui-config.yml, antora.yml, gh-pages workflow, supplemental-ui. |
| Per-module review | N agents in parallel | Each gets one module + shared_context + rule prompt files. Runs B/C/D/E/F passes. Returns `[{id, module, line, severity, message}]`. |
| Merge | Orchestrator | Flattens all findings, applies cross-module logic, deduplicates, sorts by severity. |

Consistency across agents: every agent reads the same prompt files (no rule drift), output must match the fixed JSON schema, and anything needing full-lab context lives in `shared_context`, not individual agent memory.

**Expected impact:** 6-module `verify-content` from ~8 min → ~90 sec. `create-lab` for new lab from blocking multi-step conversation to single planning exchange + parallel generation. Writing and editing phases in PH become realistic within a single session.

**Supersedes:** "Subagent-per-module execution" in Future Milestone Skills & Platform section.

### Showroom skills — spec-driven (headless) execution mode

**Origin:** Prakhar Srivastava proposal (2026-05-19). Reviewed and approved 2026-06-16.

**Problem.** PH writer currently "invokes" `create-lab` by answering its interactive questions from manifest data in the same conversation. This is context bleeding, not an interface. The manifest already contains everything the skill asks about (audience, objectives, duration, environment) — there's no reason to re-ask. And once `create-lab` becomes agent-based (see refactor above), the question-answer puppeting breaks entirely.

**The proposal.** Skills detect their caller. If a structured `ph_payload` input is present, the skill skips all interactive questions and works directly from the provided spec. If no payload, normal interactive mode for humans at the terminal. Same subagents run in both modes.

Example `create-lab` input (from PH writer):
```yaml
ph_payload:
  target_dir: content/modules/ROOT/pages/
  mode: new | continue
  previous_module: 03-module-01-pipelines.adoc
  spec:
    lab_name: ...
    audience: ...
    learning_objectives: [...]
    business_scenario: ...
    duration: 45min
    module_outline: <full outline text>
    env: {ocp_version: "4.18", attributes: {user: ..., password: ...}}
```

Returns structured JSON (`{files_created: [...], nav_updated: true, warnings: []}`) instead of conversation output. Same pattern for `verify-content` — returns `{findings: [{id, module, line, severity, message}]}` ready for `ph_store_validation_results`.

**Why this matters:** Skills become independently runnable and testable outside PH. The integration becomes a contract we can verify, not conversation context we hope flows correctly. Also unblocks any future caller (CI, portal chatbot, other tools) from using these skills programmatically.

**Depends on:** Showroom skills orchestrator refactor above (agent-based architecture needs to exist before adding the headless input path).

### Model cost optimization — right-size models, evaluate cheaper alternatives

**Origin:** Prakhar Srivastava proposal (2026-05-19). Reviewed and approved 2026-06-16.

**Guiding principle:** Reduce costs where possible, but **never at the expense of model capability**. A cheaper model that produces lower-quality content or misses review findings is not a savings — it's a regression. Every model downgrade must be validated against real output quality before shipping.

**Step 1 — Right-size Claude models (unblocked, frontmatter-only changes)**

Some skills currently default to Opus where a lighter model handles the task fine. Candidates:

| Skill | Current | Candidate | Rationale |
|---|---|---|---|
| PH orchestrator | `claude-opus-4-6` | `claude-sonnet-4-6` | Reads YAML and routes — no frontier reasoning needed |
| `showroom:verify-content` | `claude-opus-4-6` | `claude-3-5-haiku` | Rule classification + structured JSON output — needs validation |
| `showroom:create-lab` | `claude-opus-4-6` | `claude-sonnet-4-6` | Content generation — needs quality comparison before committing |

Each change requires running the skill against a real lab and comparing output quality before merging. Don't blindly swap model frontmatter.

**Step 2 — Per-agent model routing (after agent-based refactor)**

Once verify-content and create-lab use parallel subagents, each agent can declare its own model tier. Classification agents (rule-based passes) are strong candidates for Haiku. Generation agents likely need Sonnet minimum. Validate per-agent.

**Step 3 — OSS reasoning models via LiteMaaS (Phase 4 chatbot only)**

Phase 4 introduces a server-side chatbot backend that can call LiteMaaS directly (not Claude Code). This is where OSS models like `qwen3-235b` or `minimax-m2` could apply — but only if they match Claude quality for the specific tasks. Evaluate when Phase 4 is active.

**LiteMaaS pricing snapshot (2026-05-19):**

| Model | Input $/1M | Output $/1M | Notes |
|---|---|---|---|
| `claude-opus-4-6` | $5.00 | $25.00 | — |
| `claude-sonnet-4-6` | $3.00 | $15.00 | — |
| `claude-3-5-haiku` | $1.00 | $5.00 | — |
| `qwen3-235b` | $0.22 | $0.88 | thinking mode, 128K context |
| `minimax-m2` | $0.30 | $1.20 | 1M context |

**Depends on:** Step 1 independent. Step 2 depends on agent-based refactor. Step 3 depends on Phase 4 chatbot.

### Template: Zero-Touch Showroom support — COMPLETED

**Origin:** Publishing House & RCARS review (2026-06-17). **Completed 2026-06-18.**

Template now ships with both `runtime/` and `setup/` directories. Manifest includes `project.showroom_type` field (classic | zero_touch). Intake skill captures the value. Orchestrator removes the ZT directories for classic projects after intake completes.

### Approval gates with threshold-based scoring

**Origin:** Publishing House & RCARS review (2026-06-17).

Formalize the vetting phase with a scoring system. RCARS similarity scores determine the review path:

- **High similarity (≥ 98%):** Auto-block — flag as potential duplicate, require human override to proceed.
- **Medium similarity (threshold TBD):** Human reviewer required before advancing past vetting.
- **Low similarity:** Author can self-approve and proceed.

This builds on the existing RCARS vetting in the intake skill but adds structured approval logic. The threshold values need calibration against real RCARS results. The blocking behavior is optional per-project to avoid unnecessarily stalling progress.

**Depends on:** RCARS catalog search returning usable similarity scores (verify current output format).

### Express skill (cluster customization agent)
**UNBLOCKED** — both dependencies (RCARS integration + Express framework) are complete.

The agent that powers Phase 3 (Customize) of express mode. Assesses an OpenShift cluster, plans customizations from the intake design doc, executes them live (`oc` commands, operator installs, app scaffolding), and produces a recap document. Substantial piece of agent engineering — needs its own brainstorm, spec, and implementation.

### RCARS result stage-preference logic
When RCARS returns both dev and prod versions of the same CI, PH should apply stage preference based on context. Vetting prefers prod (what's live). Base-finding prefers prod (stable, orderable). Affects `ph_rcars_query` result processing in `rcars_tools.py`.

**Depends on:** RCARS dev/prod dedup fix (in progress on RCARS side).

### Express admin view in portal
Basic read-only section for express sessions — not on the kanban, but visible to admins. List express intake sessions with owner, date, base CI, status. Allow peek into intake data and cleanup of stale sessions. Lightweight table view.

### Portal user identity model
Red Hat email as primary key for user ownership across all modes. GitHub ID tracked in manifests but secondary. Need email-to-GitHub ID mapping for cross-referencing. Required for orchestrator "find projects by user" to work reliably across CC (GitHub identity) and portal (SSO/email identity).

### PH contributor guide
Skill contract spec for delegating ownership. Defines what a skill MUST read from manifest, what state it MUST update, what it MUST NOT touch (phase transitions belong to orchestrator), how it surfaces blockers (worklog entries), and how to test in isolation.

### Regression detection
PH detects that a commit touches automation or content files affecting a previously verified module and reopens the Verified task (manifest + Jira). Prevents silent regressions during multi-module development.

### MCP auth rationalization
MCP auth to portal backend is currently manual API key management. Needs a proper auth model — possibly tied to workspace identity or MaaS key. Separate design needed. Affects both local CC users and workspace users.

### CC user onboarding flow
Self-service or scripted API key generation and distribution for Claude Code users connecting to the MCP server. Current process is entirely manual.

### Express project cleanup policy
Flag or archive express intake sessions older than 30 days with status "in_progress." Prevents stale data accumulation in portal DB.

---

## Future Milestone (v2)

Deferred to a future milestone. Tracked but not in current roadmap.

### MCP & Auth
- OAuth 2.1 for MCP endpoint — upgrade path from API key auth for larger user base
- Per-key rate limiting with observability dashboard
- Hot-reload API key Secret (add/revoke keys without pod restart)
- MCP tool usage analytics (structured logs → Grafana)

### Jira
- Jira → PH write-back for manager annotations (scoped to specific fields, after one-directional sync is proven stable)
- Automated Jira issue creation from RCARS gap analysis results

### Workspace / Hosted Access
- Lightweight express mode execution — Dev Spaces is heavy for quick one-off demos. Evaluate lighter options: code-server in a pod, headless CC container, or similar. Portal↔workspace interface designed to allow backend swap without portal changes. Especially important for express mode.
- Broader audience UX — Phase 1 targets content developers. Phase 2: polish for solution architects, field engineers, PMMs. May need guided onboarding, simplified views, or a chat-like layer on top of the workspace.
- MaaS key TTL tuning — start with configurable default (7d or 30d), tune based on actual usage patterns. If key expires mid-session, user restarts workspace from portal.
- Mid-session key rotation — if usage patterns show keys expiring during active work frequently, build automated rotation. Phase 1 requires workspace restart from portal.
- Custom UDI image rebuild pipeline — periodic (monthly) rebuild for security patches, Ansible collections, base image updates. Manual for now, automate if cadence demands it.
- Multi-project workspace support (if demand emerges — currently one workspace per project)
- Token usage dashboard for MaaS key tracking per user/project
- Human-in-the-loop approval for destructive workspace actions
- Dev Spaces API exploration — evaluate full API surface for workspace env var updates (needed for key injection on resume without workspace recreation)

### Express
- RCARS express learning data — store run data (base CI + customization steps) for future accuracy improvement. Must not pollute content search results.
- RCARS infrastructure-aware metadata — index AgnosticV definitions for better base-finding

### Infrastructure
- Babylon ordering automation (manual gate works; CLI contract unstable)
- Demolition E2E testing

### Skills & Platform
- PH test harness (fixture-based skill validation before releases)
- Customizable skills (include/hook mechanism for user overrides — style, naming, review criteria)
- AI Context Modules evaluation (skills as modules with AGENTS.md, commands/, mcp.json)
- Subagent-per-module execution (for large 6+ module labs) — **superseded** by "Showroom skills — orchestrator + parallel subagent refactor" in Near-Term section
- Portal UI cleanup and refinement
- End-to-end build + deploy + onboarding (full lifecycle, no manual steps)

---

## Separate Workstreams

### AgnosticD: Split ocp4_workload_field_content
Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD apps and return immediately. Separate workstream in the AgnosticD repo, not in PH.

---

## Previously Completed

| Date | What |
|---|---|
| 2026-06-18 | ZT Showroom template support (template, manifest, intake, orchestrator) |
| 2026-06-18 | Dropped `ph_store_validation_results` wiring — review files in git are the source of truth; portal UI for this adds complexity without current value |
| 2026-05-05 | Jira integration brainstorm and design spec |
| 2026-05-05 | Backlog reorganization, doc cleanup, branch consolidation (gsd-project → main) |
| 2026-05-04 | Express mode framework (Phase 2) |
| 2026-05-01 | RCARS MCP gateway (Phase 1) |
| 2026-04-28 | Express mode design spec |
| 2026-04-27 | RCARS integration design spec |
| 2026-04-27 | Intake simplification: 3 entry paths → 2, conversational opening |
| 2026-04-27 | Phase-gate testing: Showroom and automation repo gates tested end-to-end (12 issues found and fixed) |
| 2026-04-24 | Orchestrator discovery redesign: CWD-first, one-level subdirectory scan, project selection UI |
| 2026-04-24 | Phase-gate repo creation: Orchestrator checks for Showroom/automation repos before dispatch |
| 2026-04-21 | Full skills redesign: deployment modes, worklog, smart intake, git sync, phase ordering |
| 2026-04-19 | Portal redesign: FastAPI + React + PatternFly 6 + OpenShift deployment |
| 2026-04-12 | Dashboard POC: initial portal concept |
| 2026-04-09 | Original PH design: orchestrator, intake, writer, editor, automation agents |
