---
phase: 1
slug: rcars-mcp-gateway
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | src/backend/pytest.ini or pyproject.toml |
| **Quick run command** | `cd src/backend && python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd src/backend && python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src/backend && python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd src/backend && python -m pytest tests/ -v --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | MCP-01 | T-01-01 / — | API key validated before tool dispatch | unit | `pytest tests/test_mcp_auth.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | MCP-02 | T-01-02 / — | FastMCP middleware intercepts unauthenticated calls | unit | `pytest tests/test_mcp_auth.py` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | MCP-03 | T-01-03 / — | Invalid key returns 401, no tool execution | unit | `pytest tests/test_mcp_auth.py` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | MCP-04 | — | RCARS query returns structured results | integration | `pytest tests/test_rcars_tools.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | MCP-05 | — | Catalog search returns paginated items | integration | `pytest tests/test_rcars_tools.py` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | MCP-06 | — | Catalog item returns full metadata | integration | `pytest tests/test_rcars_tools.py` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | MCP-07 | — | Health endpoint reports RCARS status | unit | `pytest tests/test_health.py` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 2 | RCARS-01 | — | SA token re-read from filesystem per request | unit | `pytest tests/test_rcars_client.py` | ❌ W0 | ⬜ pending |
| 01-04-02 | 04 | 2 | RCARS-04 | — | Cross-namespace connectivity verified | manual | N/A | N/A | ⬜ pending |
| 01-05-01 | 05 | 3 | RCARS-05 | — | Intake uses ph_rcars_query instead of curl | integration | `pytest tests/test_intake_vetting.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp_auth.py` — stubs for MCP-01, MCP-02, MCP-03
- [ ] `tests/test_rcars_tools.py` — stubs for MCP-04, MCP-05, MCP-06
- [ ] `tests/test_health.py` — stubs for MCP-07
- [ ] `tests/test_rcars_client.py` — stubs for RCARS-01, RCARS-04
- [ ] `tests/conftest.py` — shared fixtures (mock RCARS responses, test API keys)
- [ ] pytest installation — verify pytest is in dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-namespace connectivity | RCARS-04 | Requires cluster access | Run smoke test from PH pod to RCARS service |
| RCARS SA allowlist change | RCARS-02, RCARS-03 | Cross-repo Ansible deployment | Deploy RCARS with updated allowlist, verify SA token accepted |
| MCP-08 Ansible deployment | MCP-08 | Infrastructure deployment | Run Ansible deployer, verify Route/Secret/Deployment created |
| Intake vetting end-to-end | RCARS-05 | Requires Claude Code + MCP connection | Run intake with vetting on test project |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
