# Requirements: RHDP Publishing House — Milestone 2

**Defined:** 2026-04-30
**Core Value:** Content developers can create production-quality RHDP workshops and demos without juggling multiple tools, skills, or processes — one entry point orchestrates the entire pipeline from idea to published catalog item.

## v1 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### MCP Gateway

- [x] **MCP-01**: External `/mcp` HTTPS endpoint is deployed with API key authentication (SHA-256 hashed keys, `hmac.compare_digest` comparison, Ansible-managed Secret)
- [x] **MCP-02**: FastMCP 3.2+ middleware validates API key on every tool call via `on_call_tool` hook
- [x] **MCP-03**: Invalid or missing API key returns 401; valid key proceeds to tool dispatch
- [x] **MCP-04**: `ph_rcars_query(query)` tool submits RCARS advisor query, polls until complete (3s interval, 120s timeout), returns structured results with CI matches and relevance tiers
- [x] **MCP-05**: `ph_rcars_catalog_search(query, limit)` tool returns paginated RCARS catalog items
- [x] **MCP-06**: `ph_rcars_catalog_item(ci_name)` tool returns full metadata for a specific catalog item
- [x] **MCP-07**: Health check endpoint (`/health`) reports connectivity status to RCARS and other backends
- [x] **MCP-08**: Ansible deployer manages Route, API key Secret, and all K8s resource changes — no manual `oc edit` required

### RCARS Integration

- [x] **RCARS-01**: PH backend ServiceAccount token is re-read from filesystem on every RCARS request (not cached at startup)
- [x] **RCARS-02**: RCARS middleware validates SA token via Kubernetes TokenReview API (cross-repo change in `rcars-advisory`)
- [x] **RCARS-03**: PH backend ServiceAccount is added to `RCARS_SA_ALLOWLIST_STR` in RCARS Ansible vars (cross-repo change)
- [x] **RCARS-04**: Cross-namespace connectivity from `publishing-house-dev` to `rcars-dev` is verified and unblocked (NetworkPolicy check + smoke test in Ansible deploy)
- [x] **RCARS-05**: Intake skill replaces broken `curl` call with `ph_rcars_query` MCP tool reference; vetting phase runs end-to-end for both deployment modes

### Express Mode

- [ ] **EXPRESS-01**: Separate `ExpressProject` database model exists with fields: id, name, owner_email, base_ci, phase (intake/environment/customize/complete), status (in_progress/complete/abandoned), intake_data (JSONB), created_at, updated_at
- [ ] **EXPRESS-02**: `ExpressArtifact` model stores artifacts per project (artifact_type: intake_design/recap/showroom, content as text)
- [ ] **EXPRESS-03**: `ph_create_express_project(name, intake_data)` MCP tool creates an express project record in portal DB
- [ ] **EXPRESS-04**: `ph_update_express_status(project_id, phase, status)` MCP tool updates express project phase and status
- [ ] **EXPRESS-05**: `ph_store_express_artifact(project_id, artifact_type, content)` MCP tool stores recap, intake design, and other artifacts
- [ ] **EXPRESS-06**: `ph_get_express_project(project_id)` MCP tool retrieves express project state for session continuity
- [ ] **EXPRESS-07**: `ph_store_intake_results(project_id, intake_data)` and `ph_get_intake_results(project_id)` MCP tools support session continuity for onboarded/self-published modes
- [ ] **EXPRESS-08**: Orchestrator checks local manifest first, then portal via `ph_list_projects` MCP tool, then offers new intake — no more "must be in repo directory" requirement
- [ ] **EXPRESS-09**: Intake skill routes to express flow when user selects express mode; presents RCARS vetting, second RCARS base-finding query, and manual environment gate
- [ ] **EXPRESS-10**: Portal shows express projects in kanban alongside full projects (distinct card style or separate column)
- [ ] **EXPRESS-11**: Portal express project detail view shows: intake data, base CI, current phase, artifacts
- [ ] **EXPRESS-12**: Artifact viewer in portal renders recap document and intake design doc

### Jira Integration (brainstorm-first)

- [ ] **JIRA-01**: Brainstorm resolves: Jira ticket structure (epic-per-project vs. epic + phase subtasks), trigger points (which events create/update tickets), field mapping from manifest to Jira fields, and scoped write-back rules (if any fields flow Jira→PH, e.g. manager annotations, define exactly which fields and under what constraints — default is PH→Jira only)
- [ ] **JIRA-02**: Jira integration spec documents the one-directional sync contract and any approved write-back scope
- [ ] **JIRA-03**: New PH project creates a corresponding Jira ticket or epic automatically (`ph_jira_create_issue` MCP tool)
- [ ] **JIRA-04**: Phase transitions update Jira ticket status and add a comment with what changed
- [ ] **JIRA-05**: Jira comments include a link to the portal project detail view for stakeholders
- [ ] **JIRA-06**: Jira issue key is stored in the git manifest and the portal DB record for cross-referencing

### Portal Chatbot (brainstorm-first)

- [ ] **CHAT-01**: Brainstorm resolves: execution model (direct Anthropic SDK tool-use loop recommended by research vs. Claude Agent SDK), chatbot user auth model (how users log in, per-user conversation history keying), PatternFly ChatBot integration approach (evaluate PatternFly vs. custom approach to ensure UI quality is not compromised), and how chatbot avoids recreating Claude Code (focus: managed access for users without API keys, not a general AI assistant)
- [ ] **CHAT-02**: Chatbot design spec defines the "Claude-as-a-Service" model: PH holds API keys, portal users get managed access with token usage tracking
- [ ] **CHAT-03**: Portal chatbot authenticates users via portal SSO/OAuth; per-user conversation history stored in portal DB
- [ ] **CHAT-04**: Chatbot backend calls the same Python tool functions as the MCP server (no separate tool registry, no code duplication)
- [ ] **CHAT-05**: Chatbot streams responses to the user in real time; tool calls display progress ("Searching RCARS catalog...") so users see activity rather than blank screens
- [ ] **CHAT-06**: Conversation history persists in portal DB keyed by user + session; survives page refresh and reconnects
- [ ] **CHAT-07**: Chatbot UI is visually consistent with the portal and feels production-quality (not a demo-quality chat widget)
- [ ] **CHAT-08**: Users can abort in-progress responses; partial responses are preserved in conversation history

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Express Skill

- **EXPR-S-01**: Express skill (cluster customization agent) — assesses OpenShift cluster, plans and executes customizations, produces recap document. Separate brainstorm+spec+build.

### MCP Gateway — Future

- **MCP-F-01**: OAuth 2.1 for MCP endpoint — upgrade path from API key auth for larger user base
- **MCP-F-02**: Per-key rate limiting with observability dashboard

### Jira — Future

- **JIRA-F-01**: Jira-to-PH annotation sync (if brainstorm approves any write-back scope) — implement after one-directional sync is proven stable
- **JIRA-F-02**: Automated Jira issue creation from RCARS gap analysis results

### Chatbot — Future

- **CHAT-F-01**: Multi-project context switching in chatbot (start with single-project sessions)
- **CHAT-F-02**: `oc` CLI in chatbot container for express skill access
- **CHAT-F-03**: Token usage dashboard for "Claude-as-a-Service" usage tracking

### Infrastructure

- **INFRA-F-01**: Babylon ordering automation (manual environment gate works; Babylon CLI contract unstable)
- **INFRA-F-02**: Portal user identity model (Red Hat email ↔ GitHub ID mapping)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Bi-directional Jira sync (full) | Documented anti-pattern: causes duplicate creation, comment loops, and status oscillation. Any write-back must be scoped to specific fields by the Jira brainstorm phase. |
| Express skill (cluster customization agent) | Separate brainstorm+spec+build — depends on express framework but is a substantial independent workstream |
| General-purpose AI assistant chatbot | Chatbot must be scoped to PH workflows; building a general assistant recreates Claude Code and adds maintenance burden |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MCP-01 | Phase 1 | Complete (01-03) |
| MCP-02 | Phase 1 | Complete (01-03) |
| MCP-03 | Phase 1 | Complete (01-03) |
| MCP-04 | Phase 1 | Complete (01-04) |
| MCP-05 | Phase 1 | Complete (01-04) |
| MCP-06 | Phase 1 | Complete (01-04) |
| MCP-07 | Phase 1 | Complete (01-04) |
| MCP-08 | Phase 1 | Complete (01-05) |
| RCARS-01 | Phase 1 | Complete (01-02) |
| RCARS-02 | Phase 1 | Complete (01-01) |
| RCARS-03 | Phase 1 | Complete (01-01) |
| RCARS-04 | Phase 1 | Complete (01-05) |
| RCARS-05 | Phase 1 | Complete (01-06) |
| EXPRESS-01 | Phase 2 | Pending |
| EXPRESS-02 | Phase 2 | Pending |
| EXPRESS-03 | Phase 2 | Pending |
| EXPRESS-04 | Phase 2 | Pending |
| EXPRESS-05 | Phase 2 | Pending |
| EXPRESS-06 | Phase 2 | Pending |
| EXPRESS-07 | Phase 2 | Pending |
| EXPRESS-08 | Phase 2 | Pending |
| EXPRESS-09 | Phase 2 | Pending |
| EXPRESS-10 | Phase 2 | Pending |
| EXPRESS-11 | Phase 2 | Pending |
| EXPRESS-12 | Phase 2 | Pending |
| JIRA-01 | Phase 3 | Pending |
| JIRA-02 | Phase 3 | Pending |
| JIRA-03 | Phase 3 | Pending |
| JIRA-04 | Phase 3 | Pending |
| JIRA-05 | Phase 3 | Pending |
| JIRA-06 | Phase 3 | Pending |
| CHAT-01 | Phase 4 | Pending |
| CHAT-02 | Phase 4 | Pending |
| CHAT-03 | Phase 4 | Pending |
| CHAT-04 | Phase 4 | Pending |
| CHAT-05 | Phase 4 | Pending |
| CHAT-06 | Phase 4 | Pending |
| CHAT-07 | Phase 4 | Pending |
| CHAT-08 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-30*
*Last updated: 2026-04-30 after roadmap creation*
