---
phase: 02
slug: express-mode-framework
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with pytest-asyncio (backend only — no frontend changes this phase) |
| **Config file** | `rhdp-publishing-house-portal/src/backend/pyproject.toml` |
| **Quick run command** | `cd rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | EXPRESS-01 | — | N/A | integration | `python -c "from app.models import IntakeSession, ExpressMetric, Project; from app.core.types import JSONBType; print('OK')"` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | EXPRESS-01 | — | N/A | unit | `python -m pytest tests/test_models_intake_session.py tests/test_models_express_metric.py -x -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | EXPRESS-07 | — | N/A | unit (TDD) | `python -m pytest tests/test_session_tools.py -x -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | EXPRESS-08 | — | N/A | grep | `grep -c "ph_list_projects" SKILL.md && grep -c "ph_sync_manifest" SKILL.md && grep -c "PH_USER_EMAIL" SKILL.md && grep -c "MCP Availability Check" SKILL.md` | ✅ | ⬜ pending |
| 02-04-01 | 04 | 3 | EXPRESS-09 | — | N/A | grep | `grep -c "express" SKILL.md && grep -c "ph_store_intake_results" SKILL.md && grep -c "ph_record_express_run" SKILL.md && grep -c "Dead-End" SKILL.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models_intake_session.py` — stubs for IntakeSession model CRUD
- [ ] `tests/test_models_express_metric.py` — stubs for ExpressMetric model CRUD
- [ ] `tests/test_session_tools.py` — stubs for session continuity MCP tools (11 test cases per Plan 02-02)
- [ ] Shared fixtures for MCP tool testing (mock SessionLocal, mock RCARS responses)

*Note: Plans 02-03 and 02-04 modify SKILL.md files (markdown) — no test stubs needed, grep-based verification is sufficient.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Orchestrator discovers projects via MCP when no local manifest | EXPRESS-08 | Requires live MCP server and portal DB | Start PH in a directory without manifest.yaml, verify MCP query triggers |
| Express intake dead-ends at environment gate | EXPRESS-09 | Requires interactive Claude Code session | Run intake, select express, verify flow stops at environment gate message |
| Session continuity across Claude Code restart | EXPRESS-07 | Requires process restart | Store intake data, restart Claude Code, verify data retrieves from portal |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
