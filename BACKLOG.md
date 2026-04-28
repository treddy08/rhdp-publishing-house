# Publishing House — Backlog

Development backlog for the RHDP Publishing House skill suite. Session notes and completed work live in [WORKLOG.md](WORKLOG.md).

---

## Active / Near-term

### RCARS API integration for vetting
**Spec complete:** `docs/superpowers/specs/2026-04-27-rcars-integration-design.md`

Portal backend as single gateway. MCP tools (`ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`) wrap the RCARS v2 API. API key auth for CC users, SA token for cluster-internal PH→RCARS calls. External route for `/mcp` endpoint only. Needs implementation plan and build.

**Depends on:** RCARS v2 deployed (done as of 2026-04-26).

---

## Needs Brainstorm

### Express skill (cluster customization agent)
The agent that powers Phase 3 (Customize) of express mode. Assesses an OpenShift cluster, plans customizations from the intake design doc, executes them live (`oc` commands, operator installs, app scaffolding), and produces a recap document. This is the substantial piece of agent engineering — its own brainstorm, spec, and implementation.

**Depends on:** Express mode architecture (spec complete: `docs/superpowers/specs/2026-04-28-express-mode-design.md`), RCARS integration (spec complete: `docs/superpowers/specs/2026-04-27-rcars-integration-design.md`).

### Portal user identity model
Red Hat email as primary key for user ownership across all modes. GitHub ID tracked in manifests but secondary. Need email ↔ GitHub ID mapping for cross-referencing. Required for orchestrator "find projects by user" to work reliably across CC (GitHub identity) and portal (SSO/email identity).

### Portal chatbot / hosted access path
Portal chatbot for users without CC or Anthropic model access. Same PH capabilities, hosted instead of local. The portal backend already has MCP tools and RCARS integration (per the integration spec) — the chatbot consumes the same backend. Requires `oc` CLI baked into the chatbot container image for express mode.

**Connects to:** Express mode, RCARS integration, end-to-end build+deploy.

---

### PH test harness skill
A dedicated skill (`rhdp-publishing-house:test`) that validates the PH skill suite before releases. Required before PH becomes the standard for new content — a broken release cannot be discovered through hours of manual testing.

**Design direction:**
- Fixture-based: versioned project directories at known states (pre-intake, post-intake/pre-writing, mid-writing, etc.)
- Scripted inputs per fixture, run via Claude Code CLI in batch mode
- Structural assertions on file system outcomes: file existence, manifest YAML field values, gate blocking behavior
- Does NOT test content quality (LLM non-determinism) — tests gates, routing, and artifact creation
- Runs pre-release, not on every commit

**Brainstorm scope:** Fixture design, input scripting approach, assertion framework, what constitutes "passing", how to version and evolve the test suite as skills change.

---

## Medium Priority

### Customizable skills
Include/hook mechanism at the start of each skill for user overrides — writing style, naming conventions, review criteria. Users tweak behavior independently while still picking up core PH skill updates.

- Additive and optional: skills work without customizations; overrides extend, not replace
- Exception: code review, security review, and content review skills must stay standardized — quality gates are not customizable

### PH development team design / contributor spec
Keep PH modular so skill ownership can be delegated. A contributor spec defines:
- What a skill MUST read from manifest/spec before starting
- What state a skill MUST update when it completes
- What a skill MUST NOT touch (phase-level transitions belong to the orchestrator)
- How a skill surfaces blockers (worklog entries)
- How to test a skill in isolation

Not blocking current work, but should inform design decisions now so we don't paint ourselves into a corner.

### Evaluate AI Context Modules as PH foundation
Investigate whether PH skills should be structured as an AI Context Module rather than standalone skills. An AI Context Module is a superset — it wraps one or more skills alongside `AGENTS.md`, `commands/`, and `mcp.json` inside a `module/` directory, providing module-level context that applies across all skills. Reference implementation: https://github.com/LobsterTrap/lola/blob/main/docs/guides/creating-modules.md

PH currently uses standalone `SKILL.md` files in a plugin. A module structure could unify the orchestrator context (`AGENTS.md`), MCP server config (`mcp.json`), and slash commands (`commands/`) into a single coherent package — potentially replacing the current split across skills repo, portal backend, and manual MCP config.

**Goal:** Not starting from scratch. Evaluate whether the module structure gives PH a more solid foundation and how to migrate to it if so. Connects to the contributor spec and MCP orchestrator items.

### Dashboard kanban — content + automation display
Content and automation run concurrently and iterate together until both are done. The portal kanban needs a way to show this overlap without awkwardly duplicating cards or placing the project in the wrong column. Current approach (furthest-along active column) is functional but not ideal.

---

## Long-term

### End-to-end build + deploy
PH handles the full lifecycle end-to-end — someone comes with a need, PH builds the content, automation, and deploys it for them. No manual steps. Natural follow-on once prototype mode proves the model.

### MCP orchestrator
Move the orchestrator from a skill to a hosted MCP server (FastAPI on OpenShift). Exposes tools like `ph_get_status()`, `ph_advance_phase()`. Cheap structured lookups replace expensive skill-loading for routine status queries. The portal DB becomes a cache, not authoritative — manifest in git stays the source of truth.

### Subagent-per-module writing
For large labs (2+ hours, 6+ modules), isolated subagents per module could prevent context accumulation. Parked until scale is a real problem.

---

## Separate Workstreams

### AgnosticD: Split ocp4_workload_field_content
Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD apps and return immediately (no health waiting). ArgoCD eventual consistency handles operator → CR ordering. Separate workstream in the AgnosticD repo, not in PH.

---

## Completed (recent)

- **2026-04-27** — Intake simplification: 3 entry paths → 2, conversational opening for Path B, Path C merged
- **2026-04-27** — Phase-gate testing: Showroom and automation repo gates tested end-to-end; 12 issues found and fixed
- **2026-04-24** — Orchestrator discovery redesign: CWD-first, one-level subdirectory scan, project selection UI
- **2026-04-24** — Phase-gate repo creation: Orchestrator checks for Showroom/automation repos before dispatch
- **2026-04-21** — Full skills redesign: deployment modes, worklog, smart intake, git sync, phase ordering
