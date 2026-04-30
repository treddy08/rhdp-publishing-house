---
phase: 01-rcars-mcp-gateway
plan: 02
subsystem: api
tags: [httpx, async, retry, sa-token, rcars, http-client]

# Dependency graph
requires:
  - phase: 01-01
    provides: RCARS SA token auth middleware (allowlist validation)
provides:
  - RCARSClient class with full RCARS API coverage
  - RCARSError exception for structured error handling
  - SA token auth with per-request filesystem reads
  - Exponential backoff retry (3 attempts, 1s/2s/4s)
  - Advisor query with poll loop
  - Catalog search and item retrieval
  - Health check endpoint
affects: [01-03, 01-04, 01-05, 01-06, 01-07]

# Tech tracking
tech-stack:
  added: [httpx (async), pytest-asyncio]
  patterns: [async service client, exponential backoff retry, SA token per-request read, fail-fast on 4xx]

key-files:
  created:
    - rhdp-publishing-house-portal/src/backend/app/services/rcars_client.py
    - rhdp-publishing-house-portal/src/backend/tests/test_rcars_client.py
  modified:
    - rhdp-publishing-house-portal/.gitignore

key-decisions:
  - "RCARSClient uses class attribute _SA_TOKEN_PATH for testability (patchable in tests without monkeypatching global)"
  - "httpx.AsyncClient created per-request (not shared) to avoid connection pool issues across retries"

patterns-established:
  - "Async service client: __init__ takes base_url, methods return dicts, errors are typed exceptions"
  - "Retry pattern: delays list [1,2,4], fail-fast on 4xx, retry on 5xx/ConnectError/TimeoutException"
  - "SA token: read from filesystem on every _request call via _read_sa_token(), never cached"

requirements-completed: [RCARS-01]

# Metrics
duration: 4min
completed: 2026-04-30
---

# Phase 01 Plan 02: RCARS HTTP Client Summary

**Async RCARS client with SA token per-request auth, exponential backoff retry, advisor polling, and catalog search via httpx**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-30T10:47:24Z
- **Completed:** 2026-04-30T10:51:36Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- RCARSClient class providing full async API coverage for RCARS v2 (advisor query/poll, catalog search/item, health)
- SA token re-read from filesystem on every request per RCARS-01 -- never cached, supports K8s auto-rotation
- Exponential backoff retry (3 attempts, 1s/2s/4s delays) with fail-fast on 4xx per D-04
- 14 comprehensive tests covering all behaviors: token rotation, retry logic, 4xx/5xx handling, advisor polling, timeout, catalog, health

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for RCARS client** - `eb03d99` (test)
2. **Task 1 (GREEN): Implement RCARSClient** - `5532a53` (feat)
3. **Deviation: Add .venv to gitignore** - `3ae7968` (chore)

## TDD Gate Compliance

- RED gate: `eb03d99` -- test(01-02) commit exists, tests fail on import (module does not exist)
- GREEN gate: `5532a53` -- feat(01-02) commit exists after RED, all 14 tests pass
- REFACTOR gate: not needed -- implementation is clean, no refactoring required

## Files Created/Modified

- `src/backend/app/services/rcars_client.py` -- RCARSClient class with retry, SA token, advisor, catalog, health
- `src/backend/tests/test_rcars_client.py` -- 14 unit tests covering all behaviors
- `.gitignore` -- Added .venv/ to ignore list

## Decisions Made

- Used class attribute `_SA_TOKEN_PATH` instead of module global for testability -- tests can patch it per instance without affecting other tests
- Created httpx.AsyncClient per-request rather than sharing a connection pool -- avoids stale connection issues across retry attempts and simplifies error handling
- Module is standalone (no config.py import) -- callers provide base_url, keeping the client reusable and testable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added .venv to .gitignore**
- **Found during:** Task 1 (post-commit check)
- **Issue:** Created .venv for testing (pytest-asyncio not in system Python), appeared as untracked directory
- **Fix:** Added `.venv/` to portal repo .gitignore
- **Files modified:** .gitignore
- **Verification:** `git status` no longer shows .venv as untracked
- **Committed in:** 3ae7968

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor housekeeping fix. No scope creep.

## Issues Encountered

- System Python (3.12) on macOS refuses pip install without --break-system-packages (PEP 668). Created .venv in src/backend/ to install test dependencies (httpx, pytest-asyncio). This venv is gitignored and used only for local test execution.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

- RCARSClient is ready for Plan 03 (MCP tool registration) to import and use
- Plan 03 will add httpx and pytest-asyncio to requirements.txt
- The client's base_url parameter pattern means Plan 03 can wire it to config without modifying rcars_client.py

---
*Phase: 01-rcars-mcp-gateway*
*Completed: 2026-04-30*
