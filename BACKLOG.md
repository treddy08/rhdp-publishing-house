# Publishing House — Backlog

Development backlog for the RHDP Publishing House skill suite. Session notes and completed work live in [WORKLOG.md](WORKLOG.md).

---

## Top Priorities

### Jira integration (Phase 3 on roadmap)
**Needs brainstorm**

PH must create, update, and manage Jira tickets as part of the project lifecycle. Git manifest remains the source of truth for project state, but PH syncs state and updates to Jira via the Atlassian MCP server. Key questions: what triggers a Jira update (phase transitions? gate results? manual?), what's the ticket structure (one epic per project? tickets per phase?), how do we handle conflicts if someone edits Jira directly, and how does this interact with the portal DB.

**Blocker:** Jira Cloud vs. Data Center auth model unresolved — must decide before build.

### Portal chatbot (Phase 4 on roadmap)
**Needs brainstorm**

Hosted access path for users without Claude Code or Anthropic model access. The core question is how to proxy PH capabilities to users via a web UI without recreating Claude Code. Can the chatbot delegate to a Claude Code instance running on the user's behalf? What's the execution model — does the chatbot container run CC headlessly, or does it call the same MCP tools directly? Needs to support `oc` CLI for express mode. Connects to express mode, RCARS integration, and Jira integration.

**Blocker:** Anthropic SDK issue #1020 (Vertex AI streaming+tools loses tool input params) — affects chatbot UX.

### Express skill (cluster customization agent)
**Needs brainstorm — UNBLOCKED (dependencies satisfied)**

The agent that powers Phase 3 (Customize) of express mode. Assesses an OpenShift cluster, plans customizations from the intake design doc, executes them live (`oc` commands, operator installs, app scaffolding), and produces a recap document. Can be a combination of PH performing actions directly and instructing the user to perform steps manually. This is the substantial piece of agent engineering — its own brainstorm, spec, and implementation.

**Depends on:** ~~Express mode orchestration, RCARS integration~~ Both complete.

---

## Medium Priorities

### RCARS result stage-preference logic
When RCARS returns both dev and prod versions of the same CI, PH should apply stage preference based on context. Vetting prefers prod (what's live). Base-finding prefers prod (stable, orderable). Only surface dev alongside prod when the content is meaningfully different. RCARS is adding dedup for identical dev/prod pairs, but when they diverge PH needs its own logic. Affects `ph_rcars_query` result processing in `rcars_tools.py`.

**Depends on:** RCARS dev/prod dedup fix (in progress).

### Express admin view in portal
Basic read-only section in the portal for express sessions — not on the kanban, but visible to admins and power users. List express intake sessions with owner, date, base CI, status. Allow peek into intake data, and cleanup (delete stale sessions). Lightweight — table view, not full detail pages. Came up during phase 2 testing: express projects are transient but someone needs visibility into what's been created and the ability to tidy up.

### Portal user identity model
Red Hat email as primary key for user ownership across all modes. GitHub ID tracked in manifests but secondary. Need email-to-GitHub ID mapping for cross-referencing. Required for orchestrator "find projects by user" to work reliably across CC (GitHub identity) and portal (SSO/email identity).

### PH development team / contributor guide
Keep PH modular so skill ownership can be delegated. Contributors have flexibility in their lane (how they code a skill), but must adhere to the PH contract for integration. A contributor spec defines:
- What a skill MUST read from manifest/spec before starting
- What state a skill MUST update when it completes
- What a skill MUST NOT touch (phase-level transitions belong to the orchestrator)
- How a skill surfaces blockers (worklog entries)
- How to test a skill in isolation

### RCARS express learning data
Store express mode run data (selected Babylon base CI + customization steps performed) in RCARS so future express runs benefit from past experience. Needs careful design — this data must not pollute content search results (it's infrastructure/workflow data, not lab content). Could improve the base-finding query accuracy over time. Coordinate with RCARS backlog item for infrastructure-aware catalog metadata.

**Depends on:** Express skill, RCARS infrastructure-aware metadata.

---

## Everything Else

### PH test harness skill
A dedicated skill (`rhdp-publishing-house:test`) that validates the PH skill suite before releases. Fixture-based testing with versioned project directories at known states, scripted inputs run via CC CLI in batch mode, structural assertions on file system outcomes. Tests gates, routing, and artifact creation — not content quality. Runs pre-release, not on every commit.

### Customizable skills
Include/hook mechanism at the start of each skill for user overrides — writing style, naming conventions, review criteria. Additive and optional: skills work without customizations; overrides extend, not replace. Exception: code review, security review, and content review skills must stay standardized — quality gates are not customizable.

### Demolition for E2E testing
Use Demolition (RHDP's automated testing framework) for end-to-end validation of onboarded environments. Ensures that the full provisioning pipeline works — catalog item orders, environment deploys, Showroom loads, teardown completes.

### Evaluate AI Context Modules as PH foundation
Investigate whether PH skills should be structured as an AI Context Module rather than standalone skills. A module wraps one or more skills alongside `AGENTS.md`, `commands/`, and `mcp.json` — potentially replacing the current split across skills repo, portal backend, and manual MCP config. This is an implementation/architecture concern and should not block functional work in phase 0.

### Portal UI cleanup and refinement
May fold into the chatbot design since the portal UI and chatbot will likely sit side by side. Includes the dashboard kanban display for concurrent content + automation work.

### End-to-end build + deploy + onboarding
PH handles the full lifecycle end-to-end — someone comes with a need, PH builds the content, automation, and deploys it for them. No manual steps. Natural follow-on once the core modes are proven.

### Subagent-per-module execution
For large labs (2+ hours, 6+ modules), isolated subagents per module for writing, automation, etc. to ensure efficient execution without context accumulation. Parked until scale is a real problem.

---

## Separate Workstreams

### AgnosticD: Split ocp4_workload_field_content
Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD apps and return immediately (no health waiting). ArgoCD eventual consistency handles operator-to-CR ordering. Separate workstream in the AgnosticD repo, not in PH.

---

## Completed

- **2026-05-04** — Express mode framework (Phase 2): DB models (IntakeSession, ExpressMetric, JSONBType DRY), 5 session MCP tools, orchestrator MCP-aware startup with portal fallback, intake three-mode routing with express dead-end at environment gate, manifest sync, graceful MCP degradation. 4 plans, all verified. Human UAT pending for live MCP server tests.
- **2026-05-01** — RCARS MCP gateway (Phase 1): portal as single MCP gateway, API key auth via FastMCP Middleware, SA token auth for cluster-internal RCARS calls, 3 RCARS tools (`ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`), health endpoint, Ansible infrastructure (Route, Secret, volume mount), intake vetting migrated from curl to MCP tool, 5 documentation deliverables. 7 plans, all verified.
- **2026-04-28** — Express mode design spec
- **2026-04-27** — RCARS integration design spec
- **2026-04-27** — Intake simplification: 3 entry paths to 2, conversational opening for Path B, Path C merged
- **2026-04-27** — Phase-gate testing: Showroom and automation repo gates tested end-to-end; 12 issues found and fixed
- **2026-04-24** — Orchestrator discovery redesign: CWD-first, one-level subdirectory scan, project selection UI
- **2026-04-24** — Phase-gate repo creation: Orchestrator checks for Showroom/automation repos before dispatch
- **2026-04-21** — Full skills redesign: deployment modes, worklog, smart intake, git sync, phase ordering
