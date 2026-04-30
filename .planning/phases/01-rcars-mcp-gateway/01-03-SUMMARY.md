---
phase: 01-rcars-mcp-gateway
plan: 03
subsystem: auth
tags: [fastmcp, middleware, api-key, sha256, hmac, pydantic-settings]

# Dependency graph
requires:
  - phase: none
    provides: n/a (first auth plan, no prior dependency)
provides:
  - ApiKeyAuth Middleware class for MCP tool-call authentication
  - FastMCP 3.2+ server instance with middleware wiring
  - Config fields rcars_internal_url and mcp_api_key_file
  - Bumped fastmcp>=3.2.0 and httpx>=0.28.0 dependency pins
affects: [01-04-PLAN, 01-05-PLAN]

# Tech tracking
tech-stack:
  added: [fastmcp 3.2+ Middleware API, pytest-asyncio]
  patterns: [FastMCP Middleware subclass for per-tool-call auth, SHA-256 + hmac.compare_digest for timing-safe key verification, volume-mounted YAML key file for K8s Secrets]

key-files:
  created:
    - rhdp-publishing-house-portal/src/backend/tests/test_mcp_auth.py
  modified:
    - rhdp-publishing-house-portal/src/backend/app/mcp/auth.py
    - rhdp-publishing-house-portal/src/backend/app/mcp/server.py
    - rhdp-publishing-house-portal/src/backend/app/core/config.py
    - rhdp-publishing-house-portal/src/backend/requirements.txt

key-decisions:
  - "Collapsed Tasks 1 and 2 into a single GREEN commit because server.py import chain requires config.py changes (Rule 3 deviation)"
  - "Removed Keycloak JWT scaffolding entirely (KeycloakTokenVerifier, mcp_auth_enabled, keycloak_realm_url) per plan spec"

patterns-established:
  - "FastMCP Middleware pattern: subclass Middleware, override on_call_tool, use get_http_headers(include={'authorization'}) for auth header access"
  - "API key storage: YAML file with key-name -> sha256:<hex-digest> format, loaded at startup, verified with hmac.compare_digest"
  - "Conditional middleware: build _middleware list based on settings.mcp_api_key_file, pass to FastMCP constructor"

requirements-completed: [MCP-01, MCP-02, MCP-03]

# Metrics
duration: 3min
completed: 2026-04-30
---

# Phase 1 Plan 3: API Key Auth Middleware + FastMCP 3.2+ Server Upgrade Summary

**ApiKeyAuth middleware with SHA-256 + hmac.compare_digest key validation replacing Keycloak JWT scaffolding, FastMCP 3.2+ server with conditional middleware wiring**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-30T10:54:28Z
- **Completed:** 2026-04-30T10:58:07Z
- **Tasks:** 2
- **Files modified:** 5 (4 modified, 1 created)

## Accomplishments
- Replaced dead Keycloak JWT auth scaffolding with production ApiKeyAuth(Middleware) using SHA-256 hashed keys and timing-safe hmac.compare_digest comparison
- Upgraded FastMCP from >=2.0 to >=3.2.0, wired middleware into server constructor with conditional activation based on mcp_api_key_file config
- Added rcars_internal_url (cluster-internal RCARS DNS) and mcp_api_key_file (K8s Secret volume mount path) to portal config
- Created 10 unit tests covering key verification, YAML loading, missing/malformed/invalid auth rejection, and valid key pass-through

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for MCP API key auth** - `c2cde46` (test)
2. **Task 1+2 (GREEN): Replace Keycloak auth with ApiKeyAuth middleware and update config** - `b995b8e` (feat)

_Note: Tasks 1 and 2 were merged into a single GREEN commit because the import chain (conftest -> main.py -> tools.py -> server.py -> config.py) requires all changes to be present simultaneously. server.py could not be tested independently without config.py changes._

## Files Created/Modified
- `src/backend/app/mcp/auth.py` - Replaced KeycloakTokenVerifier (88 lines) with ApiKeyAuth(Middleware) (73 lines): SHA-256 hashing, hmac.compare_digest, YAML key loading, ToolError rejection
- `src/backend/app/mcp/server.py` - Replaced Keycloak scaffolding block (30 lines) with conditional ApiKeyAuth middleware wiring (20 lines)
- `src/backend/app/core/config.py` - Removed mcp_auth_enabled + keycloak_realm_url, added rcars_internal_url + mcp_api_key_file
- `src/backend/requirements.txt` - Bumped fastmcp>=3.2.0, httpx>=0.28.0, added pytest-asyncio>=0.23.0
- `src/backend/tests/test_mcp_auth.py` - 10 tests: key verification (valid/invalid/timing-safe), YAML loading (success/prefix-strip/not-found), on_call_tool (missing header/malformed/invalid key/valid key)

## Decisions Made
- Collapsed Tasks 1 and 2 into a single GREEN commit -- the import chain (conftest imports app.main which imports app.mcp.tools which imports app.mcp.server which reads config) means config.py and server.py changes must be present simultaneously for tests to run
- Kept mcp variable name in server.py (`mcp = FastMCP(...)`) to preserve tool registration pattern used by tools.py and future rcars_tools.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] server.py updated in Task 1 GREEN phase instead of Task 2**
- **Found during:** Task 1 GREEN phase (test execution)
- **Issue:** After updating config.py (removing mcp_auth_enabled), the import chain (conftest -> main.py -> tools.py -> server.py) failed because server.py still referenced settings.mcp_auth_enabled
- **Fix:** Updated server.py with the Task 2 content during the Task 1 GREEN phase to unblock test execution
- **Files modified:** src/backend/app/mcp/server.py
- **Verification:** All 78 tests pass (10 new + 68 existing)
- **Committed in:** b995b8e (Task 1+2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to unblock TDD test execution. All Task 2 acceptance criteria met. No scope creep.

## Issues Encountered
None beyond the import chain deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ApiKeyAuth middleware is ready for Plan 04 (RCARS MCP tools) to register tools on the authenticated mcp instance
- rcars_internal_url config field is ready for Plan 04's RCARSClient integration
- Plan 05 (Ansible infrastructure) will create the K8s Secret and volume mount referenced by mcp_api_key_file

## TDD Gate Compliance

- RED gate: `c2cde46` (test commit) -- tests fail on import because ApiKeyAuth does not exist
- GREEN gate: `b995b8e` (feat commit) -- all 10 tests pass after implementation
- REFACTOR gate: skipped (no cleanup needed)

## Self-Check: PASSED

- All 5 modified/created files exist on disk
- Commit c2cde46 (RED) found in git log
- Commit b995b8e (GREEN) found in git log
- SUMMARY.md exists at .planning/phases/01-rcars-mcp-gateway/01-03-SUMMARY.md

---
*Phase: 01-rcars-mcp-gateway*
*Completed: 2026-04-30*
