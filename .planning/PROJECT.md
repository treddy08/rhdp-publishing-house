# RHDP Publishing House

## What This Is

AI-powered content lifecycle management for Red Hat Demo Platform. One command — `/rhdp-publishing-house` — provides a persistent, state-aware orchestrator that manages the entire content lifecycle (intake, writing, editing, automation, review, publishing) through specialized Claude Code agent skills. Content developers become content architects: design the architecture, agents handle the writing, editing, automation, and review.

## Core Value

Content developers can create production-quality RHDP workshops and demos without juggling multiple tools, skills, or processes — one entry point orchestrates the entire pipeline from idea to published catalog item.

## Requirements

### Validated

- Orchestrator skill with state-aware project discovery, phase dispatch, and configurable autonomy (supervised/semi/full) — existing
- Intake agent with 2 entry paths (full spec, rough idea), deployment mode selection, and YAML manifest initialization — existing
- Writer agent wrapping `showroom:create-lab` and `showroom:create-demo` for module-by-module AsciiDoc generation — existing
- Editor agent wrapping `showroom:verify-content` with spec alignment checks and interactive fix loops — existing
- Automation agent with 4 sub-phases (requirements, catalog item, code generation, testing gate) supporting both Ansible and GitOps — existing
- Worklog skill for session bridging and human context (decisions, handoffs, notes, summaries) — existing
- Portal (FastAPI + React) deployed on OpenShift with kanban view, project table, phase detail, and worklog timeline — existing
- Two deployment modes: `rhdp_published` (full RHDP catalog item) and `self_published` (GitOps + generic CI) — existing
- Project template repo with manifest schema, content/automation submodule layout — existing
- Phase-gate repo creation (Showroom repo before writer, automation repo before 7c) — existing
- Git sync (pull on session start, commit+push on changes) — existing

### Active

- [ ] RCARS API integration — portal backend as MCP gateway to RCARS v2, API key auth for CC users, SA token for cluster-internal calls
- [ ] Express mode orchestration — third deployment mode for one-off disposable demo environments, portal DB state, no git repo
- [ ] Jira integration — create/update/manage Jira tickets as part of project lifecycle, manifest stays source of truth
- [ ] Portal chatbot — hosted access path for users without Claude Code or Anthropic model access

### Deferred (Future Milestones)

- Express skill (cluster customization agent) — separate brainstorm+spec+build, depends on express framework
- Portal user identity model (email to GitHub mapping) — after express framework ships
- PH development team / contributor guide — skill contracts, state management boundaries, isolated testing
- PH test harness — fixture-based skill validation before releases
- Customizable skills (include/hook mechanism) — additive, not blocking functional work
- Demolition E2E testing — after core modes are proven
- AI Context Modules evaluation — architecture investigation, not blocking functional work
- Babylon ordering automation — manual gate works for now
- RCARS infrastructure-aware metadata — filed in RCARS backlog, not PH work
- Subagent-per-module execution — parked until scale is a real problem
- Portal UI cleanup — may fold into chatbot design
- End-to-end build+deploy+onboarding — natural follow-on once core modes are proven

### Out of Scope

- Mobile app — web-first, PH is a developer tool
- Real-time collaboration — manifest + git handles handoffs

## Context

**Multi-repo architecture:**
- `rhdp-publishing-house` — dev repo (skills source, docs, specs, template submodule)
- `rhdp-publishing-house-skills` — published skills plugin (submodule in dev repo as `skills-plugin`)
- `rhdp-publishing-house-portal` — portal backend (FastAPI) + frontend (React), deployed on OpenShift
- `rhdp-publishing-house-template` — project template (submodule in dev repo as `template`)
- `rcars-advisory` (separate project) — RCARS v2 API, deployed in `rcars-dev` namespace

**Infrastructure:**
- Portal deployed in `publishing-house-dev` namespace on OpenShift
- RCARS v2 deployed in `rcars-dev` namespace (same cluster) — available as of 2026-04-26
- Cross-namespace communication via K8s service DNS
- Ansible deployers manage all secrets, config, and deployments

**Design specs complete:**
- RCARS integration: `docs/superpowers/specs/2026-04-27-rcars-integration-design.md`
- Express mode: `docs/superpowers/specs/2026-04-28-express-mode-design.md`

**What works today:** Full lifecycle for onboarded and self-published modes — intake through automation. Code/security review and final review skills are not yet implemented but are not in this milestone's scope.

## Constraints

- **Multi-repo:** Changes span `rhdp-publishing-house`, `rhdp-publishing-house-portal`, `rhdp-publishing-house-skills`, and `rcars-advisory`. GSD tracks work centrally but commits happen in each repo.
- **Dependency chain:** RCARS integration must land before express mode (express needs MCP tools). Jira and chatbot brainstorms are independent of each other but benefit from RCARS being in place.
- **RCARS v2 API stability:** RCARS v2 is deployed but the API surface may evolve. PH wraps RCARS behind MCP tools so skill code is insulated from API changes.
- **Auth model:** API key auth for external MCP access, SA token for cluster-internal RCARS calls. No OAuth for this milestone.
- **Ansible deployers:** All infrastructure changes (routes, secrets, config) go through Ansible — no manual `oc edit`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Portal backend as single MCP gateway | Avoids duplicate integration logic; serves both CC and chatbot users | — Pending |
| API key auth for MCP endpoint | Simple, sufficient for internal team; OAuth is overkill | — Pending |
| SA token auth for RCARS (cluster-internal) | Zero-config, K8s manages token lifecycle | — Pending |
| Express state in portal DB, not git manifest | Express projects are ephemeral — git overhead not justified | — Pending |
| Git manifest remains source of truth for onboarded/self-published | Proven pattern, works offline, supports handoffs | ✓ Good |
| Jira and chatbot start as brainstorm+spec, build deferred | Dependencies not fully resolved, better to design right than build twice | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-30 after initialization*
