# Phase 1: RCARS MCP Gateway - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticated MCP endpoint wrapping RCARS v2, fixing the broken intake vetting. Claude Code users can query RCARS through authenticated MCP tools (`ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`), and intake vetting works end-to-end again — with graceful degradation when MCP is unavailable. Includes API key auth for external access, SA token auth for cluster-internal RCARS calls, health check endpoint, Ansible-managed infrastructure, and full documentation.

</domain>

<decisions>
## Implementation Decisions

### API key lifecycle
- **D-01:** Pod restart for key changes in Phase 1 — backend reads API keys from the volume-mounted Secret file at startup only. No hot-reload mechanism. To add or revoke a key: update Ansible vars, redeploy, pod restarts.
- **D-02:** Manual key generation workflow: `openssl rand -hex 32`, SHA-256 hash, paste into Ansible vars file, redeploy. No CLI helper tooling. Document the workflow clearly in the admin guide.
- **D-03:** API keys stored as a volume-mounted K8s Secret file (not env var). Leaves the door open for hot-reload later without changing the storage approach.

### RCARS client resilience
- **D-04:** Retry with exponential backoff (3 attempts, 1s/2s/4s delays) in the RCARS HTTP client layer for transient failures (5xx, connection errors). Fail fast on 4xx (auth errors). Skills never see transient failures — they get the final result or a clean "RCARS unavailable" error.
- **D-05:** Moderate error verbosity — include enough context for developer diagnosis (retry count, failure type, service name) but no raw stack traces. Example: "RCARS query failed after 3 retries (connection timeout to rcars-api service). Vetting skipped."
- **D-06:** Health endpoint (`/health`) actively probes RCARS on every request (calls RCARS health or lightweight endpoint). Reports accurate real-time connectivity status.

### Cross-repo work plan
- **D-07:** Dependency order execution: (1) RCARS SA allowlist change in `rcars-advisory` → (2) Portal backend MCP gateway in `rhdp-publishing-house-portal` → (3) Intake skill update in `rhdp-publishing-house-skills` → (4) Documentation in `rhdp-publishing-house`. Each step verifiable before the next.
- **D-08:** Config changes only for RCARS — prepare the Ansible vars change and document the deploy command. User runs the deployer manually. No automated deployment during plan execution.
- **D-09:** Branch strategy: `gsd-project` branch for all PH repos (portal, skills-plugin, this repo). Direct commits to `main` for `rcars-advisory` (rcars-dev builds from main, rcars-prod builds from production — we only touch dev).
- **D-10:** Submodule awareness: `skills-plugin` and `template` are git submodules in `rhdp-publishing-house`. Changes committed through the main dev repo. Local clones of these repos must be pulled after commits to stay in sync.

### Documentation
- **D-11:** All 5 documentation deliverables ship alongside code, not after. Documentation is a first-class requirement. If RCARS documentation needs updating to match the integration, those changes are in scope too (committed to `rcars-advisory` main).
- **D-12:** All documentation lives in this repo (`rhdp-publishing-house`) under `docs/`, even for features implemented in the portal repo. Single source of truth for PH docs.

### Claude's Discretion
- FastMCP 2.0 → 3.2+ migration approach (how to handle breaking changes)
- httpx AsyncClient configuration (connection pooling, timeout values beyond the spec's 120s advisor timeout)
- RCARS HTTP client module structure (single module vs. service class)
- Exact health check probe implementation (which RCARS endpoint to call)
- Keycloak auth scaffolding removal approach (clean delete vs. gradual replacement)

</decisions>

<specifics>
## Specific Ideas

- Future API key management vision: browser-based callback authenticating via Red Hat SSO — not for this phase, but the storage approach (volume-mounted Secret) should not paint us into a corner
- User is "not happy with the portal repo being separate" — potential future consolidation. For now, docs centralize in this repo even though code is in the portal repo
- Skills should stay simple — retry/resilience logic lives in the backend HTTP client layer, not in skill code

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### RCARS integration design
- `docs/superpowers/specs/2026-04-27-rcars-integration-design.md` — Complete integration architecture: auth model (API key + SA token), MCP tool contracts (`ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`), network topology, deployment changes, verification checklist, documentation deliverables

### Existing MCP server code (portal repo)
- `rhdp-publishing-house-portal:src/backend/app/mcp/server.py` — Current FastMCP 2.0 server setup with unused Keycloak auth scaffolding (to be replaced with API key auth via FastMCP 3.2+ Middleware)
- `rhdp-publishing-house-portal:src/backend/app/mcp/auth.py` — Keycloak JWT verifier (to be removed and replaced)
- `rhdp-publishing-house-portal:src/backend/app/mcp/tools.py` — Existing MCP tools (`ph_list_projects`, `ph_get_launch_instructions`, `ph_store_validation_results`, `ph_get_validation_results`) — pattern to follow for new RCARS tools

### Intake skill (broken vetting)
- `skills-plugin/skills/intake/SKILL.md` — Lines 216-260: broken `curl` call to RCARS `/recommend` endpoint. Must be replaced with `ph_rcars_query` MCP tool reference

### Requirements
- `.planning/REQUIREMENTS.md` — MCP-01 through MCP-08 and RCARS-01 through RCARS-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/mcp/server.py`: FastMCP server instance (`mcp = FastMCP(...)`) — upgrade to 3.2+, add Middleware for API key auth
- `app/mcp/tools.py`: Existing tool pattern using `@mcp.tool()` decorator with `SessionLocal()` for DB sessions — new RCARS tools follow same pattern (but use httpx instead of DB sessions)
- `app/core/config.py`: Pydantic settings — add RCARS endpoint URL, API key file path, and health check config

### Established Patterns
- MCP tools manage their own sessions (DB or HTTP client) since they run outside FastAPI request lifecycle
- FastMCP mounted at `/mcp` path in the FastAPI app via `mcp.streamable_http_app()` pattern
- Ansible deployer manages all K8s resources (Secrets, Routes, Deployments) — no manual `oc` commands

### Integration Points
- `app/mcp/server.py` line 9: `mcp` FastMCP instance — RCARS tools register here
- Portal FastAPI `main.py`: MCP app mount point — Route and auth middleware connect here
- Ansible deployer in `rhdp-publishing-house-portal/ansible/`: Route and Secret resources managed here
- RCARS Ansible in `rcars-advisory/ansible/`: SA allowlist env var managed here

</code_context>

<deferred>
## Deferred Ideas

- Browser-based API key provisioning via Red Hat SSO callback — future milestone, replaces manual openssl+ansible workflow
- Portal repo consolidation into main dev repo — user flagged dissatisfaction with separate portal repo
- Hot-reload for API key Secret — volume-mount storage choice preserves this option for later

</deferred>

---

*Phase: 01-rcars-mcp-gateway*
*Context gathered: 2026-04-30*
