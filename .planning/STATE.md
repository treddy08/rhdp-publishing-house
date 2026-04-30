---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 1 context gathered
last_updated: "2026-04-30T12:00:00Z"
last_activity: 2026-04-30 -- Completed plan 01-05 (Ansible infrastructure -- Route, Secret, volume mount, cross-namespace verified)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 7
  completed_plans: 5
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-30)

**Core value:** Content developers can create production-quality RHDP workshops and demos without juggling multiple tools, skills, or processes -- one entry point orchestrates the entire pipeline from idea to published catalog item.
**Current focus:** Phase 01 — rcars-mcp-gateway

## Current Position

Phase: 01 (rcars-mcp-gateway) — EXECUTING
Plan: 6 of 7
Status: Executing Phase 01
Last activity: 2026-04-30 -- Completed plan 01-05 (Ansible infrastructure -- Route, Secret, volume mount, cross-namespace verified)

Progress: [███████░░░] 71%

## Performance Metrics

**Velocity:**

- Total plans completed: 5
- Average duration: 12min
- Total execution time: 1.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-rcars-mcp-gateway | 5/7 | 61min | 12min |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Portal backend as single MCP gateway (avoids duplicate integration logic)
- API key auth for MCP endpoint (simple, sufficient for internal team)
- SA token auth for RCARS cluster-internal calls (zero-config, K8s manages lifecycle)
- Express state in portal DB not git manifest (ephemeral projects, git overhead not justified)
- Jira and chatbot start as brainstorm+spec (design right before building)
- RCARS API test files go in src/api/tests/ (API has own pyproject.toml with test config)
- All RCARS auth functions are async (require_curator/require_admin cascade from async require_auth)
- RCARSClient uses _SA_TOKEN_PATH class attribute for testability (patchable per instance)
- httpx.AsyncClient created per-request (not shared) to avoid connection pool issues across retries
- FastMCP Middleware pattern for auth (subclass Middleware, override on_call_tool, get_http_headers with include={"authorization"})
- Keycloak JWT scaffolding fully removed (never activated, replaced by API key auth)
- RCARS MCP tools instantiate RCARSClient per-call (not shared) matching per-request httpx pattern
- Health endpoint top-level status always "ok" -- RCARS is a sub-check (K8s probe compatibility)
- FastMCP 3.2+ mount uses combine_lifespans + app re-creation pattern
- MCP Route targets backend service with 180s timeout (120s RCARS advisor polling + overhead)
- API key Secret uses stringData with sha256: prefix via Jinja2 dict2items
- Webhook builds removed, replaced with per-component Ansible tags (build_backend, build_frontend)
- Resource limits parameterized in common.yml defaults (not hardcoded in templates)

### Pending Todos

None yet.

### Blockers/Concerns

- ~~RCARS SA token auth (RCARS_SA_ALLOWLIST_STR) exists in config but is not yet wired into RCARS auth middleware~~ RESOLVED in plan 01-01 (commits a7bfa90, e1394e5 on rcars-advisory main)
- Jira Cloud vs. Data Center auth model unconfirmed -- must resolve before Phase 3 build
- Anthropic SDK issue #1020 (Vertex AI streaming+tools loses tool input params) -- affects Phase 4 chatbot UX

## Deferred Items

Items acknowledged and carried forward:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Express | Express skill (cluster customization agent) | v2 -- depends on express framework | Milestone 2 init |
| MCP | OAuth 2.1 for MCP endpoint | v2 -- overkill for current user base | Milestone 2 init |
| Chatbot | Multi-project context switching | v2 -- start with single-project sessions | Milestone 2 init |

## Session Continuity

Last session: 2026-04-30T12:00:00Z
Stopped at: Completed 01-05-PLAN.md
Resume file: .planning/phases/01-rcars-mcp-gateway/01-06-PLAN.md
