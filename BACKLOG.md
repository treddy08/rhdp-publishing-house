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
- [ ] New Jira project created (need project admin approval)
- [ ] Jira service account provisioned on redhat.atlassian.net
- [ ] Initiative issue type available in new project
- [ ] Jira Cloud vs. Data Center auth confirmed (believed Cloud, need to verify service account process)

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

### PH editor — wire `ph_store_validation_results`

**Origin:** Prakhar Srivastava proposal (2026-05-19). Reviewed and approved 2026-06-16.

**Problem.** The editor skill runs `showroom:verify-content`, captures findings in conversation context, and stops there. The `ph_store_validation_results` MCP tool exists and is live on the portal — it just isn't being called.

**The fix.** One additional step in `skills/editor/SKILL.md`: after verify-content finishes, call `ph_store_validation_results` with the structured findings JSON. Portal kanban then shows per-module verification status without anyone having to ask what the results were.

**Status:** Unblocked. PH skills change only, no Showroom changes needed. Can ship independently before the agent refactor.

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
