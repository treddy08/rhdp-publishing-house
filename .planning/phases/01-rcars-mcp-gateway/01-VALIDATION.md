---
phase: 1
slug: rcars-mcp-gateway
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 1 -- Validation Strategy

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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 01-01-01 | 01 | 1 | RCARS-02 | T-01-01 | SA token validated via K8s TokenReview + allowlist | unit | `pytest tests/test_auth_middleware.py` | TDD (created in Plan 01 Task 1) |
| 01-01-02 | 01 | 1 | RCARS-03 | T-01-03 | SA allowlist wired through Ansible env var | manual | `grep sa_allowlist ansible/vars/dev.yml` | config verification |
| 01-02-01 | 02 | 1 | RCARS-01 | T-01-08 | SA token re-read from filesystem per request | unit | `pytest tests/test_rcars_client.py` | TDD (created in Plan 02 Task 1) |
| 01-03-01 | 03 | 1 | MCP-01 | T-01-10 | API key validated before tool dispatch (SHA-256 + hmac) | unit | `pytest tests/test_mcp_auth.py` | TDD (created in Plan 03 Task 1) |
| 01-03-02 | 03 | 1 | MCP-02 | T-01-13 | FastMCP middleware intercepts unauthenticated calls | unit | `pytest tests/test_mcp_auth.py` | TDD (created in Plan 03 Task 1) |
| 01-03-03 | 03 | 1 | MCP-03 | T-01-11 | Invalid key returns ToolError, no tool execution | unit | `pytest tests/test_mcp_auth.py` | TDD (created in Plan 03 Task 1) |
| 01-04-01 | 04 | 2 | MCP-04 | T-01-15 | RCARS query returns structured results | unit | `pytest tests/test_rcars_tools.py` | TDD (created in Plan 04 Task 1) |
| 01-04-02 | 04 | 2 | MCP-05 | -- | Catalog search returns paginated items | unit | `pytest tests/test_rcars_tools.py` | TDD (created in Plan 04 Task 1) |
| 01-04-03 | 04 | 2 | MCP-06 | -- | Catalog item returns full metadata | unit | `pytest tests/test_rcars_tools.py` | TDD (created in Plan 04 Task 1) |
| 01-04-04 | 04 | 2 | MCP-07 | T-01-16 | Health endpoint reports RCARS status | unit | `pytest tests/test_health.py` | TDD (created in Plan 04 Task 2) |
| 01-05-01 | 05 | 2 | MCP-08 | T-01-19 | Ansible templates have Route, Secret, volume mount | config | `grep -c mcp-api-keys ansible/templates/manifests-*.yaml.j2` | config verification |
| 01-05-02 | 05 | 2 | RCARS-04 | -- | Cross-namespace connectivity verified | manual | N/A | checkpoint:human-verify |
| 01-06-01 | 06 | 3 | RCARS-05 | T-01-23 | Intake uses ph_rcars_query instead of curl | grep | `grep -c ph_rcars_query skills-plugin/skills/intake/SKILL.md` | content verification |
| 01-07-01 | 07 | 3 | MCP-01,04-08 | T-01-25 | All 5 documentation deliverables exist | content | `ls docs/architecture/rcars-integration.md docs/admin/mcp-auth.md docs/admin/rcars-service-auth.md docs/user/claude-code-setup.md docs/api/mcp-tools.md` | content verification |

---

## Wave 0 Requirements

Plans 01, 02, 03, and 04 use TDD approach -- test files are created alongside implementation within each task (not as separate Wave 0 stubs). This satisfies the Nyquist rule because every code-producing task creates its test file as part of the RED-GREEN cycle.

- [x] `tests/test_auth_middleware.py` -- created in Plan 01 Task 1 (TDD)
- [x] `tests/test_rcars_client.py` -- created in Plan 02 Task 1 (TDD)
- [x] `tests/test_mcp_auth.py` -- created in Plan 03 Task 1 (TDD)
- [x] `tests/test_rcars_tools.py` -- created in Plan 04 Task 1 (TDD)
- [x] `tests/test_health.py` -- extended in Plan 04 Task 2 (existing file)
- [x] pytest-asyncio -- added to requirements.txt in Plan 03 Task 1

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

- [x] All tasks have `<automated>` verify or TDD test creation within the task
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered via TDD approach (tests created alongside code)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
