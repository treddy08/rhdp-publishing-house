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

### Phase 4: Portal Chatbot — NEEDS BRAINSTORM

**Goal:** Users without Claude Code or Anthropic API access get managed PH capabilities through a hosted web UI.

**Status:** Needs brainstorm. No spec yet.

**Key questions to resolve:**
- Execution model: direct Anthropic SDK tool-use loop vs Claude Agent SDK (research recommends direct SDK — ~50 lines, no framework overhead)
- User auth: OAuth proxy headers provide identity, but tool-level authorization not designed
- PatternFly ChatBot integration: evaluate @patternfly/chatbot v6.4.1 vs custom approach
- Scope boundaries: PH workflows only, not a general AI assistant
- Chatbot serves ALL modes (onboarded, self-published, express) — not just express

**Known blocker:** Anthropic SDK issue #1020 (Vertex AI streaming+tools loses tool input params). Workaround exists: disable streaming for tool-use requests. Monitor upstream.

**Requirements:** CHAT-01 through CHAT-08

**Stack additions needed:** anthropic[vertex] >=0.97.0, @patternfly/chatbot >=6.4.1, sse-starlette >=2.0.0

---

## Near-Term (Post-Milestone 2)

Items that are unblocked or nearly unblocked. Not on the current roadmap but high value.

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

### Chatbot
- Multi-project context switching (start with single-project sessions)
- `oc` CLI in chatbot container for express skill access
- Token usage dashboard for "Claude-as-a-Service" tracking
- Human-in-the-loop approval for destructive chatbot actions
- Thinking/reasoning visibility (extended thinking, collapsible UI)

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
- Subagent-per-module execution (for large 6+ module labs)
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
