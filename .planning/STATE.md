---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: Completed 02-03-PLAN.md
last_updated: "2026-05-04T09:35:30.702Z"
last_activity: 2026-05-04
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-30)

**Core value:** Content developers can create production-quality RHDP workshops and demos without juggling multiple tools, skills, or processes -- one entry point orchestrates the entire pipeline from idea to published catalog item.
**Current focus:** Phase 02 — express-mode-framework

## Current Position

Phase: 02 (express-mode-framework) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
Last activity: 2026-05-04

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 7
- Average duration: 15min
- Total execution time: 1.8 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-rcars-mcp-gateway | 7/7 | 105min | 15min |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 02 P01 | 4min | 2 tasks | 13 files |
| Phase 02 P02 | 3min | 1 task | 4 files |
| Phase 02 P03 | 4min | 1 task | 1 file |
| Phase 02 P04 | 3min | 1 tasks | 1 files |

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
- Documentation directory structure: docs/architecture/ for system-level, docs/admin/ for runbooks, docs/user/ for end-user guides, docs/api/ for API references
- [Phase ?]: JSONBType extracted to app/core/types.py as single shared definition (DRY refactor from 3 duplicates)
- [Phase ?]: IntakeSession uses JSONB for intake_data (schema-flexible, mirrors manifest shape per D-08)
- [Phase ?]: sync_source column on Manifest for multi-writer conflict prevention (github vs mcp)
- [Phase ?]: owner_email on Project is nullable (existing projects have no email per Pitfall 4)
- [Phase 02]: Session tools are sync functions (not async) -- DB-only operations, no external I/O
- [Phase 02]: ph_list_projects dual filter: owner_email OR owner_github (email username portion) for backward compatibility
- [Phase 02]: yaml.safe_load for manifest parsing in ph_sync_manifest (T-02-04 mitigation)
- [Phase 02]: MCP availability check probes ph_list_projects once at session start (T-02-10 mitigation)
- [Phase 02]: Portal fallback queries both projects and unclaimed intake sessions for comprehensive discovery
- [Phase 02]: Manifest sync is silent on success, warns on failure without blocking workflow
- [Phase 02]: Added "show me my portal projects" routing entry for on-demand portal query (D-05)
- [Phase 02]: Deployment mode selection moved from intake interview to post-vetting step (enables express as third option)
- [Phase 02]: Express intake stores data in portal DB only via ph_store_intake_results (no local manifest per D-04)
- [Phase 02]: MCP unavailability hides express option with explanation, presents only two modes (Pitfall 6 / T-02-14)

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

Last session: 2026-05-04T09:35:16.162Z
Stopped at: Completed 02-04-PLAN.md
Resume file: None
