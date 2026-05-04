# Phase 2: Express Mode Framework - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Orchestrator evolution and session continuity — the state layer that lets PH discover projects via the portal, persist intake data across sessions, and support multiple clients (Claude Code today, chatbot later). Express intake routing is included as a lightweight addition (third mode option that dead-ends at the environment gate until the express skill is built separately). This phase does NOT build the express skill, portal express project tracking, or express-specific portal UI.

**Scope restructuring (from original roadmap):** The original Phase 2 spec assumed express projects would be tracked as durable portal objects with lifecycle management, kanban views, and artifact storage. User decision: express is throwaway — PH helps get the environment, hands it over, and forgets about it. The only persisted express data is metrics (run counts, automation vs. manual breakdown) and, eventually, RCARS learning data (backlogged — needs design to avoid polluting content search). This dramatically simplifies the phase to focus on the orchestrator and session continuity work that benefits ALL modes and enables the Phase 4 chatbot.

</domain>

<decisions>
## Implementation Decisions

### Express mode philosophy
- **D-01:** Express projects are NOT tracked as "projects" in the portal. They are transient workflows — PH helps build the environment and walks away. No lifecycle tracking, no kanban presence, no portal detail views.
- **D-02:** Express metrics are tracked — count of express runs, how many were fully automated (post-Babylon) vs. had manual steps. Lightweight aggregate data only.
- **D-03:** RCARS learning data (storing selected base CI + customization steps from express runs to improve future runs) is backlogged. Needs careful design to avoid polluting content search results. Added to both PH and RCARS backlogs.
- **D-04:** Express intake data lives in portal DB only (no local file, no git repo). The express skill reads it from the portal when it eventually runs.

### Orchestrator startup flow
- **D-05:** Local manifest first, portal on demand. If a manifest exists locally, use it. If not found, query portal via MCP automatically. User can explicitly request portal project list anytime. Include a hint: "If you don't see your project here, ask for a list from the portal."
- **D-06:** When MCP is unavailable (no API key, server down), warn the user and block portal-dependent features. List what's unavailable (session continuity, express mode, portal project discovery). Proceed with local-only mode.
- **D-07:** User identification: check for a configured email first (PH config file or environment variable). If not found, prompt on first portal query and cache locally. One-time setup, then automatic.

### Session continuity & portal sync
- **D-08:** Portal DB mirrors manifest schema — same core project data shape. Portal can augment with portal-specific fields (UI state, express session data), but core project data is identical. Either source (manifest or portal DB) can bootstrap the other.
- **D-09:** Portal DB updated on every manifest write. Every time a skill updates the manifest, it also pushes to the portal via MCP. Real-time sync, not batched.
- **D-10:** This session continuity layer is the critical foundation for the Phase 4 chatbot. The chatbot is just another client of the same portal state — different frontend, same backend data.

### Intake routing
- **D-11:** Intake presents three deployment modes after vetting (onboarded, self-published, express). User selects. PH never steers toward a mode.
- **D-12:** Express intake runs a second RCARS base-finding query (broader, infrastructure-focused). Quality is limited until RCARS gets infrastructure-aware catalog metadata — currently relies on content analysis as a proxy.
- **D-13:** Express flow dead-ends at the environment gate for now ("order this Babylon environment, come back when it's ready"). No express skill to continue with until that's built separately.

### Cross-repo work
- **D-14:** Same patterns as Phase 1: `gsd-project` branch for PH repos, submodule awareness for `skills-plugin`, docs centralize in `rhdp-publishing-house` under `docs/`.

### Claude's Discretion
- Portal DB schema details for manifest mirroring (which fields, JSONB vs. normalized columns)
- MCP tool contracts for session continuity (`ph_store_intake_results`, `ph_get_intake_results` — may need redesign given the manifest-mirror approach)
- Express metrics storage mechanism (DB table, counter, or metrics endpoint)
- User email caching format and location (dotfile, config file, etc.)
- How manifest→portal sync handles conflicts or stale data

</decisions>

<specifics>
## Specific Ideas

- The portal DB should not have a meaningfully different data set from the manifest for onboarded/self-published modes — same shape, portal augments with its own needs
- Express mode's value proposition: "I need a working environment by Thursday" — speed over durability
- RCARS learning data should eventually feed back into the base-finding query to improve accuracy, but this needs infrastructure-aware catalog metadata first (both are backlogged)
- The orchestrator evolution pattern (check local → query portal → new intake) defines the contract that both Claude Code and the future chatbot use — CC checks local first, chatbot skips to portal

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Express mode design
- `docs/superpowers/specs/2026-04-28-express-mode-design.md` — Original express mode architecture. Note: scope restructured per this CONTEXT.md — express project tracking, portal express UI, and lifecycle management are removed. Orchestrator evolution, intake routing, and session continuity sections remain relevant.

### RCARS integration (Phase 1 foundation)
- `docs/superpowers/specs/2026-04-27-rcars-integration-design.md` — MCP tool contracts, auth model, network topology. Phase 2 adds tools on the same infrastructure.

### Existing orchestrator skill
- `skills-plugin/skills/orchestrator/SKILL.md` — Current startup flow (manifest discovery only). Must be updated for portal MCP awareness.

### Existing intake skill
- `skills-plugin/skills/intake/SKILL.md` — Current intake flow (two modes). Must be updated for three-mode routing and portal DB persistence.

### Existing MCP tools (portal repo)
- `rhdp-publishing-house-portal:src/backend/app/mcp/tools.py` — Pattern for new session continuity MCP tools

### Phase 1 context (prior decisions)
- `.planning/phases/01-rcars-mcp-gateway/01-CONTEXT.md` — Cross-repo patterns, MCP tool patterns, documentation approach

### Requirements
- `.planning/REQUIREMENTS.md` — EXPRESS-01 through EXPRESS-12 (note: several requirements will need rescoping to match restructured phase scope)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/mcp/tools.py` (portal repo): Existing MCP tool pattern with `@mcp.tool()` decorator — new session continuity tools follow same pattern
- `app/models/` (portal repo): Existing SQLAlchemy models — manifest-mirror schema extends these
- `app/core/config.py` (portal repo): Pydantic settings — add user email config, session continuity settings

### Established Patterns
- MCP tools manage their own sessions (DB or HTTP client) — from Phase 1
- Manifest YAML is the local source of truth for onboarded/self-published modes
- Orchestrator dispatches to skills based on phase — routing logic lives in orchestrator SKILL.md
- Skills read manifest before starting, update it when done

### Integration Points
- Orchestrator startup: currently reads `publishing-house/manifest.yaml` — needs MCP query fallback
- Intake skill: currently writes manifest locally — needs to also push to portal via MCP
- All skills that update manifest: need a sync-to-portal hook on every write
- Portal MCP server: new tools register alongside existing RCARS tools

</code_context>

<deferred>
## Deferred Ideas

- RCARS express learning data — store base CI + customization steps for future run improvement. Added to PH and RCARS backlogs. Needs design to avoid polluting content search.
- Express portal UI (kanban, detail views, artifact viewer) — removed from Phase 2. May revisit if express usage patterns warrant it.
- Express project lifecycle tracking — removed. Express is throwaway.
- Babylon ordering automation — manual gate works for now.
- Portal user identity model (email to GitHub mapping) — separate workstream, not blocking this phase.

</deferred>

---

*Phase: 02-express-mode-framework*
*Context gathered: 2026-05-04*
