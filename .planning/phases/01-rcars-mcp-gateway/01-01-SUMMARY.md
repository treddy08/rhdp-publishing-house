---
phase: 01-rcars-mcp-gateway
plan: 01
subsystem: auth
tags: [kubernetes, tokenreview, serviceaccount, fastapi, httpx, ansible]

# Dependency graph
requires: []
provides:
  - "RCARS dual auth middleware (SA Bearer token + OAuth proxy headers)"
  - "SA allowlist wired through Ansible deployment templates"
  - "K8s TokenReview-based SA token validation"
affects: [01-rcars-mcp-gateway, rcars-advisory]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "K8s TokenReview API for SA token validation (not self-parsed JWT)"
    - "Dual auth: SA Bearer token checked first, falls through to OAuth proxy headers"
    - "SA allowlist as CSV env var, parsed into set for O(1) lookup"

key-files:
  created:
    - "rcars-advisory/src/api/tests/test_auth_middleware.py"
  modified:
    - "rcars-advisory/src/api/rcars/api/middleware/auth.py"
    - "rcars-advisory/ansible/templates/manifests-app.yaml.j2"
    - "rcars-advisory/ansible/vars/dev.yml.example"

key-decisions:
  - "Placed test file in src/api/tests/ (API package test directory) instead of top-level tests/ per actual project structure"
  - "Made require_curator and require_admin async (Rule 3) since they call async require_auth"
  - "Used module-level Path constants for K8s SA token and CA cert paths for testability"

patterns-established:
  - "Async auth middleware: all auth functions (get_current_user, require_auth, require_curator, require_admin) are async"
  - "SA allowlist pattern: comma-separated env var -> set[str] for O(1) membership check"
  - "TokenReview pattern: POST to K8s API with pod SA token, verify response status.authenticated + username in allowlist"

requirements-completed: [RCARS-02, RCARS-03]

# Metrics
duration: 6min
completed: 2026-04-30
---

# Phase 01 Plan 01: RCARS SA Token Auth Summary

**Dual auth in RCARS middleware -- K8s ServiceAccount tokens validated via TokenReview API alongside existing OAuth proxy headers, with Ansible-wired SA allowlist**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-30T10:37:52Z
- **Completed:** 2026-04-30T10:43:51Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- RCARS auth middleware accepts both SA Bearer tokens (new) and OAuth proxy X-Forwarded-Email headers (existing)
- SA tokens validated via K8s TokenReview API with 5-second timeout and explicit allowlist
- 19 unit tests covering all auth paths: allowlist parsing, token validation, get_current_user dual path, require_auth 401
- Ansible templates and vars wired for SA allowlist deployment via existing CSV join pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SA token validation to RCARS auth middleware with unit tests** - `a7bfa90` (feat)
2. **Task 2: Wire SA allowlist through RCARS Ansible templates and vars** - `e1394e5` (feat)

Note: All commits are on `rcars-advisory` repo `main` branch (per D-09).

## Files Created/Modified
- `src/api/rcars/api/middleware/auth.py` - Dual auth middleware with _validate_sa_token, _parse_sa_allowlist, async get_current_user/require_auth/require_curator/require_admin
- `src/api/tests/test_auth_middleware.py` - 19 unit tests for all auth paths and edge cases
- `ansible/templates/manifests-app.yaml.j2` - RCARS_SA_ALLOWLIST_STR env var in API deployment
- `ansible/vars/dev.yml.example` - sa_allowlist variable with placeholder SA identity
- `ansible/vars/dev.yml` (local only, gitignored) - sa_allowlist with PH backend SA identity

## Decisions Made
- **Test location:** Tests placed in `src/api/tests/` (API package test directory) rather than top-level `tests/` because the auth middleware is part of the API package which has its own pyproject.toml and test infrastructure
- **Async cascade:** Made `require_curator` and `require_admin` async since they call `require_auth` which is now async -- FastAPI Depends() handles async deps transparently
- **Module-level Path constants:** K8s token and CA cert paths defined as module-level constants (`_K8S_TOKEN_PATH`, `_K8S_CA_PATH`) to enable clean patching in tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made require_curator and require_admin async**
- **Found during:** Task 1 (auth middleware modification)
- **Issue:** Plan only specified making get_current_user and require_auth async, but require_curator and require_admin directly call require_auth. If require_auth is async, callers must also be async.
- **Fix:** Converted both functions to async def, using await for require_auth calls
- **Files modified:** src/api/rcars/api/middleware/auth.py
- **Verification:** All 19 tests pass; all route Depends() usages are in async route handlers
- **Committed in:** a7bfa90 (Task 1 commit)

**2. [Rule 3 - Blocking] Corrected test file location**
- **Found during:** Task 1 (unit test creation)
- **Issue:** Plan specified `tests/test_auth_middleware.py` (top-level) but the API package has its own test infrastructure at `src/api/tests/` with its own pyproject.toml (asyncio_mode = "auto", testpaths = ["tests"]). Tests at the top-level directory could not import `rcars.api.middleware.auth`.
- **Fix:** Placed test file at `src/api/tests/test_auth_middleware.py` and ran tests from `src/api/` directory
- **Files modified:** src/api/tests/test_auth_middleware.py
- **Verification:** All 19 tests pass with correct imports
- **Committed in:** a7bfa90 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep. The async cascade is a direct consequence of making require_auth async. The test location matches the actual project structure.

## Issues Encountered
- Virtual environment needed creation (.venv) for test execution -- project had no pre-existing venv. Created and installed `src/api[dev]` package. The .venv is gitignored.
- Pre-existing test failure in `test_config.py::test_use_vertex` due to `ANTHROPIC_VERTEX_PROJECT_ID` env var being set in developer environment -- unrelated to this plan's changes.

## User Setup Required

None - no external service configuration required. User must run the RCARS Ansible deployer to apply the SA allowlist env var to the cluster (per D-08), but this is an existing operational process.

## Next Phase Readiness
- RCARS auth middleware is ready for PH backend SA token calls
- SA allowlist is configured in dev.yml for `system:serviceaccount:publishing-house-dev:default`
- Plans 02-07 can proceed (RCARS client module, MCP tools, API key auth, etc.)
- Deployer must be run to activate the SA allowlist on the cluster

## Self-Check: PASSED

- All 4 created/modified files exist on disk
- Both task commits (a7bfa90, e1394e5) verified in rcars-advisory git log
- 19/19 unit tests passing

---
*Phase: 01-rcars-mcp-gateway*
*Completed: 2026-04-30*
