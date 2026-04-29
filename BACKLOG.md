# Publishing House — Backlog

Development backlog for the RHDP Publishing House skill suite. Session notes and completed work live in [WORKLOG.md](WORKLOG.md).

---

## Top Priorities

### RCARS API integration
**Spec complete:** `docs/superpowers/specs/2026-04-27-rcars-integration-design.md`

Portal backend as single gateway. MCP tools (`ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`) wrap the RCARS v2 API. API key auth for CC users, SA token for cluster-internal PH→RCARS calls. External route for `/mcp` endpoint only. This is also where lightweight orchestrator queries land — `ph_get_status()`, `ph_list_projects()` — so routine "where am I at?" checks return structured data in a few hundred tokens instead of loading the full orchestrator skill context. Needs implementation plan and build.

**Depends on:** RCARS v2 deployed (done as of 2026-04-26).

### Express mode orchestration
**Spec complete:** `docs/superpowers/specs/2026-04-28-express-mode-design.md`

Third deployment mode for one-off, disposable demo environments. Orchestrator gains portal/MCP awareness (check local manifest → portal → new intake). Intake routes to express flow when selected. Portal DB stores express project state and artifacts. No git repo required for express projects.

**Depends on:** RCARS integration (above).

### Jira integration
**Needs brainstorm**

PH must create, update, and manage Jira tickets as part of the project lifecycle. Git manifest remains the source of truth for project state, but PH syncs state and updates to Jira via the Atlassian MCP server. Key questions: what triggers a Jira update (phase transitions? gate results? manual?), what's the ticket structure (one epic per project? tickets per phase?), how do we handle conflicts if someone edits Jira directly, and how does this interact with the portal DB. Needs a deep brainstorming session before any design work.

### Portal chatbot
**Needs brainstorm**

Hosted access path for users without Claude Code or Anthropic model access. The core question is how to proxy PH capabilities to users via a web UI without recreating Claude Code. Can the chatbot delegate to a Claude Code instance running on the user's behalf? What's the execution model — does the chatbot container run CC headlessly, or does it call the same MCP tools directly? Needs to support `oc` CLI for express mode. Connects to express mode, RCARS integration, and Jira integration.

---

## Medium Priorities

### Express skill (cluster customization agent)
The agent that powers Phase 3 (Customize) of express mode. Assesses an OpenShift cluster, plans customizations from the intake design doc, executes them live (`oc` commands, operator installs, app scaffolding), and produces a recap document. Can be a combination of PH performing actions directly and instructing the user to perform steps manually. This is the substantial piece of agent engineering — its own brainstorm, spec, and implementation.

**Depends on:** Express mode orchestration, RCARS integration.

### Portal user identity model
Red Hat email as primary key for user ownership across all modes. GitHub ID tracked in manifests but secondary. Need email ↔ GitHub ID mapping for cross-referencing. Required for orchestrator "find projects by user" to work reliably across CC (GitHub identity) and portal (SSO/email identity).

### PH development team / contributor guide
Keep PH modular so skill ownership can be delegated. Contributors have flexibility in their lane (how they code a skill), but must adhere to the PH contract for integration. A contributor spec defines:
- What a skill MUST read from manifest/spec before starting
- What state a skill MUST update when it completes
- What a skill MUST NOT touch (phase-level transitions belong to the orchestrator)
- How a skill surfaces blockers (worklog entries)
- How to test a skill in isolation

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
Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD apps and return immediately (no health waiting). ArgoCD eventual consistency handles operator → CR ordering. Separate workstream in the AgnosticD repo, not in PH.

---

## Completed (recent)

- **2026-04-28** — Express mode design spec
- **2026-04-27** — RCARS integration design spec
- **2026-04-27** — Intake simplification: 3 entry paths → 2, conversational opening for Path B, Path C merged
- **2026-04-27** — Phase-gate testing: Showroom and automation repo gates tested end-to-end; 12 issues found and fixed
- **2026-04-24** — Orchestrator discovery redesign: CWD-first, one-level subdirectory scan, project selection UI
- **2026-04-24** — Phase-gate repo creation: Orchestrator checks for Showroom/automation repos before dispatch
- **2026-04-21** — Full skills redesign: deployment modes, worklog, smart intake, git sync, phase ordering
