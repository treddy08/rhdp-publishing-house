---
phase: 02-express-mode-framework
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, pydantic, jsonb, postgresql, sqlite]

# Dependency graph
requires:
  - phase: 01-rcars-mcp-gateway
    provides: "Portal backend with existing models (Project, Manifest, Phase, WorklogEntry, ValidationRun) and test infrastructure"
provides:
  - "IntakeSession model for session continuity across all modes"
  - "ExpressMetric model for lightweight express run counters"
  - "Shared JSONBType in app/core/types.py (DRY refactor)"
  - "owner_email column on Project model for user filtering"
  - "sync_source column on Manifest model for circular sync prevention"
  - "Pydantic schemas for IntakeSession (Create + Response)"
  - "Alembic migration chaining from 0402588c6e4a"
affects: [02-02, 02-03, 02-04, 04-chatbot]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared type definitions in app/core/types.py"
    - "JSONB column for session data storage (schema-flexible)"
    - "sync_source column pattern for multi-source data conflict prevention"

key-files:
  created:
    - "rhdp-publishing-house-portal/src/backend/app/core/types.py"
    - "rhdp-publishing-house-portal/src/backend/app/models/intake_session.py"
    - "rhdp-publishing-house-portal/src/backend/app/models/express_metric.py"
    - "rhdp-publishing-house-portal/src/backend/app/schemas/intake_session.py"
    - "rhdp-publishing-house-portal/src/backend/alembic/versions/a1b2c3d4e5f6_add_intake_sessions_express_metrics.py"
    - "rhdp-publishing-house-portal/src/backend/tests/test_models_intake_session.py"
    - "rhdp-publishing-house-portal/src/backend/tests/test_models_express_metric.py"
  modified:
    - "rhdp-publishing-house-portal/src/backend/app/models/manifest.py"
    - "rhdp-publishing-house-portal/src/backend/app/models/validation.py"
    - "rhdp-publishing-house-portal/src/backend/app/models/phase.py"
    - "rhdp-publishing-house-portal/src/backend/app/models/project.py"
    - "rhdp-publishing-house-portal/src/backend/app/models/__init__.py"
    - "rhdp-publishing-house-portal/src/backend/alembic/env.py"

key-decisions:
  - "JSONBType extracted to app/core/types.py as single shared definition (was duplicated in 3 model files)"
  - "IntakeSession uses JSONB for intake_data (schema-flexible, mirrors manifest shape without normalized columns per D-08)"
  - "sync_source column on Manifest defaults to 'github' and is set to 'mcp' by ph_sync_manifest (prevents Pitfall 1 circular sync)"
  - "owner_email on Project is nullable (existing projects have no email per Pitfall 4)"
  - "Migration written manually (alembic autogenerate requires existing DB schema comparison)"

patterns-established:
  - "Shared type imports: from app.core.types import JSONBType"
  - "sync_source pattern for multi-writer conflict prevention on Manifest"

requirements-completed: [EXPRESS-01]

# Metrics
duration: 4min
completed: 2026-05-04
---

# Phase 02 Plan 01: Database Foundation Summary

**IntakeSession and ExpressMetric models with shared JSONBType, sync_source conflict prevention, and 8 model-level tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-04T09:05:43Z
- **Completed:** 2026-05-04T09:10:16Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Extracted duplicated JSONBType from 3 model files to single shared location in app/core/types.py
- Created IntakeSession model with JSONB intake_data, owner_email index, status tracking, and mode field for all three deployment modes
- Created ExpressMetric model with owner_email index and automated flag for lightweight express run counters
- Added owner_email column to Project and sync_source column to Manifest for circular sync prevention
- Created Alembic migration chaining from previous migration (0402588c6e4a)
- Created Pydantic schemas (IntakeSessionCreate, IntakeSessionResponse) following validation.py pattern
- All 8 new tests pass, full suite of 95 tests green with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract JSONBType, create IntakeSession + ExpressMetric models, add sync_source** - `43a5c59` (feat)
2. **Task 2: Create Alembic migration and model-level unit tests** - `0ce499d` (feat)

## Files Created/Modified
- `app/core/types.py` - Shared JSONBType TypeDecorator (platform-independent JSONB)
- `app/models/intake_session.py` - IntakeSession ORM model with JSONB intake_data
- `app/models/express_metric.py` - ExpressMetric ORM model for express run counters
- `app/schemas/intake_session.py` - Pydantic schemas for IntakeSession create/response
- `app/models/manifest.py` - Removed local JSONBType, added sync_source column
- `app/models/validation.py` - Removed local JSONBType, imports from shared
- `app/models/phase.py` - Removed local JSONBType, imports from shared
- `app/models/project.py` - Added owner_email column (nullable)
- `app/models/__init__.py` - Added IntakeSession and ExpressMetric exports
- `alembic/env.py` - Added IntakeSession and ExpressMetric model imports
- `alembic/versions/a1b2c3d4e5f6_*.py` - Migration for new tables and columns
- `tests/test_models_intake_session.py` - 5 IntakeSession model tests
- `tests/test_models_express_metric.py` - 3 ExpressMetric model tests

## Decisions Made
- JSONBType extracted to `app/core/types.py` as the single source of truth (eliminated 3 duplicate definitions)
- IntakeSession.intake_data uses JSONB (not normalized columns) per D-08 manifest-mirror approach
- sync_source column on Manifest defaults to "github"; ph_sync_manifest (Plan 02) will set it to "mcp" to prevent circular sync (RESEARCH.md Pitfall 1)
- owner_email on Project is nullable because existing projects have no email (RESEARCH.md Pitfall 4)
- Alembic migration written manually because autogenerate requires an existing DB with prior schema applied; followed exact pattern from previous migration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing alembic package in venv**
- **Found during:** Task 2 (migration generation)
- **Issue:** alembic was listed in requirements.txt but not installed in the local .venv
- **Fix:** Ran `pip install alembic` in the portal backend venv
- **Files modified:** None (venv only, not committed)
- **Verification:** `python -c "import alembic"` succeeds

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal -- alembic installation was a missing dev dependency. No scope creep.

## Issues Encountered
None beyond the alembic installation noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Database models are ready for Plan 02 (MCP session tools) to build on
- IntakeSession and ExpressMetric are importable and tested
- sync_source column on Manifest is ready for ph_sync_manifest implementation
- owner_email column on Project is ready for ph_list_projects filtering
- Full test suite green (95 tests)

## Self-Check: PASSED

All 7 created files verified present. Both task commits (43a5c59, 0ce499d) verified in git log.

---
*Phase: 02-express-mode-framework*
*Completed: 2026-05-04*
