# Roadmap: RHDP Publishing House -- Milestone 2 (Superpowers)

## Overview

This milestone extends the Publishing House from a local-only Claude Code workflow into a platform with authenticated API access, a third deployment mode, Jira visibility for stakeholders, and a hosted chatbot for users without Claude Code. The MCP gateway is the foundation -- every subsequent phase consumes its tools. Express mode proves portal-based state management. Jira and chatbot each start with a design brainstorm before building, ensuring the right thing gets built.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: RCARS MCP Gateway** - Authenticated MCP endpoint wrapping RCARS v2, fixing broken intake vetting
- [ ] **Phase 2: Express Mode Framework** - Third deployment mode for disposable demo environments with portal-only state
- [ ] **Phase 3: Jira Integration** - One-directional Jira sync for stakeholder visibility into project lifecycle
- [ ] **Phase 4: Portal Chatbot** - Hosted access path giving users without Claude Code the same PH capabilities

## Phase Details

### Phase 1: RCARS MCP Gateway
**Goal**: Claude Code users can query RCARS through authenticated MCP tools, and intake vetting works end-to-end again — with graceful degradation when MCP is unavailable
**Depends on**: Nothing (first phase)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07, MCP-08, RCARS-01, RCARS-02, RCARS-03, RCARS-04, RCARS-05
**Success Criteria** (what must be TRUE):
  1. A Claude Code user with a valid API key can connect to the `/mcp` endpoint and invoke `ph_rcars_query` to get advisor results
  2. A Claude Code user can browse RCARS catalog items via `ph_rcars_catalog_search` and retrieve full metadata via `ph_rcars_catalog_item`
  3. An unauthenticated or invalid-key request to `/mcp` is rejected with 401 -- no tool execution occurs
  4. The `/health` endpoint reports RCARS connectivity status without requiring authentication
  5. Running intake with vetting on a new project successfully queries RCARS through the MCP tool (no more broken curl calls)
  6. When the MCP server is unavailable or the user has no API key configured, intake notes the limitation and continues without vetting — no blocking, no crash
**Plans**: 7 plans

Plans:
- [x] 01-01-PLAN.md — RCARS SA token auth middleware + Ansible allowlist wiring
- [x] 01-02-PLAN.md — RCARS HTTP client with retry, SA token, and config updates
- [ ] 01-03-PLAN.md — API key auth middleware + FastMCP 3.2+ server upgrade
- [ ] 01-04-PLAN.md — RCARS MCP tools + health endpoint + main.py wiring
- [ ] 01-05-PLAN.md — Ansible infrastructure (Route, Secret, volume mount)
- [ ] 01-06-PLAN.md — Intake skill vetting update (curl to MCP tool)
- [ ] 01-07-PLAN.md — Documentation (5 deliverables)

### Phase 2: Express Mode Framework
**Goal**: The express mode plumbing exists — DB model, MCP tools, orchestrator awareness, portal tracking — so express projects can be created and tracked even before the express skill (cluster customization agent) is built
**Depends on**: Phase 1
**Note**: This phase delivers the framework only. The express skill (Phase 3 of the express mode, where the agent actually customizes the cluster) is a separate workstream outside this milestone. Express projects created here will sit at the "environment" gate awaiting the skill.
**Requirements**: EXPRESS-01, EXPRESS-02, EXPRESS-03, EXPRESS-04, EXPRESS-05, EXPRESS-06, EXPRESS-07, EXPRESS-08, EXPRESS-09, EXPRESS-10, EXPRESS-11, EXPRESS-12
**Success Criteria** (what must be TRUE):
  1. A user can select express mode during intake, go through RCARS vetting, identify a base CI, and have their express project created and tracked in the portal DB
  2. The orchestrator discovers existing projects by checking local manifest first, then querying portal via MCP -- no longer requires being in a repo directory
  3. Portal kanban shows express projects alongside full projects with a visually distinct card style
  4. Portal express project detail view displays intake data, base CI, current phase, and stored artifacts (recap, intake design)
  5. Session continuity works for all modes -- intake results persist in portal DB and survive Claude Code restarts
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Jira Integration
**Goal**: Stakeholders can follow project progress in Jira without leaving their existing workflow, and managers have enough visibility to assess timeline health
**Depends on**: Phase 1
**Requirements**: JIRA-01, JIRA-02, JIRA-03, JIRA-04, JIRA-05, JIRA-06
**Success Criteria** (what must be TRUE):
  1. A brainstorm document exists that resolves ticket structure, trigger points, field mapping, write-back scope, and progress estimation model (how to calculate % complete vs expected at a given date for milestone tracking) -- reviewed and approved before any build work begins
  2. Creating a new PH project automatically creates a corresponding Jira ticket or epic with correct field mapping
  3. Phase transitions update the Jira ticket status and add a comment with a link to the portal project detail view
  4. The Jira issue key is stored in both the git manifest and portal DB record, enabling cross-referencing from either direction
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Portal Chatbot
**Goal**: Portal users without Claude Code or Anthropic API access get managed PH capabilities through a hosted web UI — PH holds the API keys and delivers Claude-as-a-Service, not a general AI assistant and not a recreation of Claude Code
**Depends on**: Phase 1
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08
**Success Criteria** (what must be TRUE):
  1. A brainstorm document exists that resolves execution model, user auth, PatternFly ChatBot integration, and chatbot scope boundaries -- reviewed and approved before any build work begins
  2. An authenticated portal user can open the chatbot, ask a question, and see the response stream in real time
  3. The chatbot calls the same Python tool functions as the MCP server -- tool calls display progress indicators ("Searching RCARS catalog...") rather than blank screens
  4. Conversation history persists across page refreshes and reconnects, keyed by user and session
  5. Users can abort an in-progress response; partial responses are preserved in history
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4
Note: Phases 3 and 4 both depend on Phase 1 but are independent of each other. They are ordered 3 then 4 because Phase 4 benefits from having Phases 2-3 tools available.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. RCARS MCP Gateway | 2/7 | Executing | - |
| 2. Express Mode Framework | 0/0 | Not started | - |
| 3. Jira Integration | 0/0 | Not started | - |
| 4. Portal Chatbot | 0/0 | Not started | - |
