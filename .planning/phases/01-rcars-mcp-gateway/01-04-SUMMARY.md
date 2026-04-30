---
phase: 01-rcars-mcp-gateway
plan: 04
subsystem: mcp
tags: [fastmcp, rcars, mcp-tools, health-probe, async, httpx]

# Dependency graph
requires:
  - phase: 01-02
    provides: RCARSClient class with advisor, catalog, health methods
  - phase: 01-03
    provides: FastMCP 3.2+ server instance with ApiKeyAuth middleware, config settings
provides:
  - Three RCARS MCP tools (ph_rcars_query, ph_rcars_catalog_search, ph_rcars_catalog_item)
  - Active RCARS health probe in /health endpoint (D-06)
  - FastMCP 3.2+ mount with combined lifespans in main.py
  - Graceful degradation on RCARS unavailability (error dict, not exception)
affects: [01-05, 01-06, 01-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [async MCP tools with per-tool RCARSClient instantiation, graceful degradation via RCARSError catch, combine_lifespans for FastMCP 3.2+ app recreation, active health sub-check that does not fail K8s probes]

key-files:
  created:
    - rhdp-publishing-house-portal/src/backend/app/mcp/rcars_tools.py
  modified:
    - rhdp-publishing-house-portal/src/backend/app/api/health.py
    - rhdp-publishing-house-portal/src/backend/app/main.py
    - rhdp-publishing-house-portal/src/backend/tests/test_health.py
    - rhdp-publishing-house-portal/src/backend/tests/test_rcars_tools.py

key-decisions:
  - "Tools instantiate RCARSClient per-call (not shared) matching the per-request pattern from rcars_client.py"
  - "Health endpoint top-level status always 'ok' -- RCARS status is a sub-check that does not fail K8s liveness/readiness probes"
  - "Empty query string converts to None before passing to catalog_search (empty string vs no filter)"

patterns-established:
  - "Async MCP tool pattern: @mcp.tool() async def, instantiate RCARSClient with settings.rcars_internal_url, catch RCARSError and return {'error': str(e), 'status': 'unavailable'}"
  - "Health sub-check pattern: Optional Pydantic model field, active probe with try/except, report status without failing top-level"
  - "FastMCP 3.2+ mount: http_app(path='/'), combine_lifespans(app_lifespan, mcp_app.lifespan), re-create FastAPI app with same metadata/CORS/routers"

requirements-completed: [MCP-04, MCP-05, MCP-06, MCP-07]

# Metrics
duration: 3min
completed: 2026-04-30
---

# Phase 01 Plan 04: RCARS MCP Tools + Health Probe + FastMCP 3.2+ Mount Summary

**Three async RCARS MCP tools (query, catalog search, catalog item) with graceful degradation, active health probe, and FastMCP 3.2+ combined lifespan mount**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-30T11:02:25Z
- **Completed:** 2026-04-30T11:05:52Z
- **Tasks:** 2 (Task 1: TDD RED+GREEN, Task 2: auto)
- **Files created:** 2
- **Files modified:** 3

## Accomplishments

- Three RCARS MCP tools registered on the authenticated mcp instance: ph_rcars_query (advisor polling), ph_rcars_catalog_search (paginated browse), ph_rcars_catalog_item (full metadata)
- Active RCARS health probe (D-06) in /health endpoint -- reports connectivity without failing K8s probes
- FastMCP 3.2+ mount with combine_lifespans replacing legacy streamable_http_app fallback pattern
- 10 new tests (7 RCARS tools + 3 health), all 87 tests in the suite pass

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for RCARS MCP tools** - `adc7072` (test)
2. **Task 1 (GREEN): Implement three RCARS MCP tools** - `f414ffe` (feat)
3. **Task 2: Health probe + main.py mount** - `211455c` (feat)

## TDD Gate Compliance

- RED gate: `adc7072` -- test(01-04) commit exists, tests fail on import (module does not exist)
- GREEN gate: `f414ffe` -- feat(01-04) commit exists after RED, all 7 tests pass
- REFACTOR gate: not needed -- implementation is clean, no refactoring required

## Files Created/Modified

- `src/backend/app/mcp/rcars_tools.py` -- Three RCARS MCP tools with @mcp.tool() decorators and RCARSError graceful degradation
- `src/backend/app/api/health.py` -- RCARSHealthStatus model, async health_check with active RCARS probe
- `src/backend/app/main.py` -- RCARS tools side-effect import, FastMCP 3.2+ combined lifespan mount
- `src/backend/tests/test_rcars_tools.py` -- 7 tests covering success, unavailable, not found, and parameter scenarios
- `src/backend/tests/test_health.py` -- 3 tests: basic health, RCARS ok, RCARS unavailable (200 on degradation)

## Decisions Made

- Tools instantiate RCARSClient per-call rather than sharing a singleton -- matches the httpx.AsyncClient per-request pattern established in Plan 02 and avoids lifecycle issues with MCP tools running outside FastAPI request scope
- Health endpoint top-level status is always "ok" even when RCARS is down -- K8s liveness/readiness probes check HTTP 200 status, not response body; RCARS connectivity is a sub-check for observability
- Empty query string ("") is converted to None before passing to catalog_search -- distinguishes between "no filter" and "filter by empty string"

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- All three RCARS MCP tools are registered and operational for Plan 05 (Ansible infrastructure) and Plan 06 (smoke test)
- Health endpoint is ready for Plan 05's K8s deployment verification
- FastMCP 3.2+ mount pattern is complete -- no further main.py changes needed for MCP

## Self-Check: PASSED

- All 6 created/modified files exist on disk
- Commit adc7072 (RED) found in git log
- Commit f414ffe (GREEN) found in git log
- Commit 211455c (Task 2) found in git log
- SUMMARY.md exists at .planning/phases/01-rcars-mcp-gateway/01-04-SUMMARY.md

---
*Phase: 01-rcars-mcp-gateway*
*Completed: 2026-04-30*
