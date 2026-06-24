# Publishing House — Backlog & Roadmap

**Migrated to Jira (2026-06-24).** Active backlog is tracked in RHDPCD under:

- **Initiative:** [RHDPCD-24 — Content Development Tools](https://redhat.atlassian.net/browse/RHDPCD-24)
- **Epic:** [RHDPCD-26 — Publishing House](https://redhat.atlassian.net/browse/RHDPCD-26)

Future Milestone (v2) items not yet migrated — they'll become Jira tasks when promoted to active work.

---

## Future Milestone (v2)

Deferred to a future milestone. Not in current roadmap. Will be migrated to Jira when promoted.

### MCP & Auth
- OAuth 2.1 for MCP endpoint — upgrade path from API key auth for larger user base
- Per-key rate limiting with observability dashboard
- Hot-reload API key Secret (add/revoke keys without pod restart)
- MCP tool usage analytics (structured logs → Grafana)

### Jira
- Jira → PH write-back for manager annotations (scoped to specific fields, after one-directional sync is proven stable)
- Automated Jira issue creation from RCARS gap analysis results

### Workspace / Hosted Access
- Lightweight express mode execution — Dev Spaces is heavy for quick one-off demos
- Broader audience UX — polish for solution architects, field engineers, PMMs
- MaaS key TTL tuning, mid-session key rotation, custom UDI rebuild pipeline
- Multi-project workspace support, token usage dashboard
- Human-in-the-loop approval for destructive workspace actions
- Dev Spaces API exploration for key injection on resume

### Express
- RCARS express learning data — store run data for future accuracy improvement
- RCARS infrastructure-aware metadata — index AgnosticV definitions for better base-finding

### Infrastructure
- Babylon ordering automation (manual gate works; CLI contract unstable)
- Demolition E2E testing

### Skills & Platform
- PH test harness (fixture-based skill validation before releases)
- Customizable skills (include/hook mechanism for user overrides)
- AI Context Modules evaluation (skills as modules with AGENTS.md, commands/, mcp.json)
- Portal UI cleanup and refinement
- End-to-end build + deploy + onboarding (full lifecycle, no manual steps)

---

## Separate Workstreams

### AgnosticD: Split ocp4_workload_field_content
Split into `field_content_cluster` + `field_content_tenant` roles. Separate workstream in the AgnosticD repo, not in PH.

---

## Previously Completed

| Date | What |
|---|---|
| 2026-06-24 | Backlog migrated to Jira (RHDPCD-26 under RHDPCD-24) |
| 2026-06-18 | ZT Showroom template support (template, manifest, intake, orchestrator) |
| 2026-06-18 | Dropped `ph_store_validation_results` wiring |
| 2026-05-05 | Jira integration brainstorm and design spec |
| 2026-05-05 | Backlog reorganization, doc cleanup, branch consolidation |
| 2026-05-04 | Express mode framework (Phase 2) |
| 2026-05-01 | RCARS MCP gateway (Phase 1) |
| 2026-04-28 | Express mode design spec |
| 2026-04-27 | RCARS integration design spec |
| 2026-04-27 | Intake simplification: 3 entry paths → 2, conversational opening |
| 2026-04-27 | Phase-gate testing end-to-end (12 issues found and fixed) |
| 2026-04-24 | Orchestrator discovery redesign |
| 2026-04-24 | Phase-gate repo creation |
| 2026-04-21 | Full skills redesign |
| 2026-04-19 | Portal redesign: FastAPI + React + PatternFly 6 + OpenShift deployment |
| 2026-04-12 | Dashboard POC |
| 2026-04-09 | Original PH design |
