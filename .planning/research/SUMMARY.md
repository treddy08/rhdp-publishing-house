# Project Research Summary

**Project:** RHDP Publishing House -- Milestone 2 (Superpowers)
**Domain:** AI-powered content lifecycle management -- MCP gateway, express provisioning, Jira integration, portal chatbot
**Researched:** 2026-04-30
**Confidence:** MEDIUM-HIGH

## Executive Summary

This milestone extends the Publishing House platform with four new capability layers: (1) an authenticated MCP gateway that wraps RCARS and future backends behind a unified tool interface, (2) an express provisioning mode for disposable demo environments with portal-only state, (3) one-directional Jira integration for stakeholder visibility, and (4) a portal chatbot that gives users without Claude Code access the same PH capabilities through a web UI. The research is unanimous on one point: the MCP gateway is the foundation -- every other capability depends on it, and it must ship first and correctly.

The recommended approach is conservative and dependency-driven. FastMCP 3.2+ (upgrade from the current >=2.0 pin) provides the middleware and auth primitives needed for the gateway. The portal backend remains the single integration surface -- no separate gateway service, no separate chatbot service. The same MCP tool functions serve both Claude Code users (via MCP protocol over HTTPS) and chatbot users (via direct Python function calls from the LLM proxy). This "one codebase, one tool set" pattern is the most critical architectural decision and prevents the tool-definition drift that plagues multi-path systems.

The primary risks are concentrated in Phase 1 infrastructure: FastMCP mount path double-prefixing (documented in MCP Python SDK issue #1367), CORS middleware collision between FastAPI and FastMCP, bound SA token expiration on OpenShift 4.11+, and cross-namespace NetworkPolicy blocking. All of these have known solutions documented in the pitfalls research, but every one of them will cause silent or confusing failures if not addressed proactively. The Jira and chatbot phases carry design risk rather than infrastructure risk -- both need brainstorm+spec work before building, and the research identifies clear anti-patterns to avoid (bi-directional Jira sync, general-purpose chat UI, LangChain/agent framework overhead).

## Key Findings

### Recommended Stack

The stack additions are minimal and well-targeted. No new frameworks, no paradigm shifts -- each addition solves exactly one problem.

**Core technologies (new this milestone):**
- **FastMCP >=3.2.0** (upgrade): MCP server framework with `Middleware` class for API key auth at the tool-call level. The v3.x `on_call_tool` hook with `get_http_headers()` dependency injection is the officially documented pattern for API key validation.
- **httpx >=0.28.0** (bump): Async HTTP client for cross-namespace RCARS API calls with SA token auth. Already in deps, just needs a version bump.
- **atlassian-python-api >=4.0.7**: Thin Jira REST API client. Chosen over the Atlassian Remote MCP Server (which is designed for interactive LLM-user access, not programmatic backend sync) and over `jira` (pycontribs, which adds object abstraction PH does not need).
- **anthropic[vertex] >=0.97.0**: Direct Anthropic SDK for chatbot LLM proxy. Chosen over LiteLLM (supply chain compromise risk, single-provider overhead) and LangChain (50+ transitive deps for a 50-line tool-use loop).
- **@patternfly/chatbot >=6.4.1**: Official PatternFly AI chat components. Non-negotiable given PH is a PatternFly application -- mixing design systems doubles CSS maintenance and creates visual inconsistency.
- **sse-starlette >=2.0.0**: SSE streaming for chatbot responses. SSE is preferred over WebSockets because the communication is unidirectional (server-to-client for LLM tokens), SSE auto-reconnects, and it works natively through OpenShift Routes without WebSocket upgrade configuration.

**Removed:** Keycloak JWT auth scaffolding (`KeycloakTokenVerifier` in `app/mcp/auth.py`). Never activated, replaced by API key auth.

**Known issue:** Anthropic SDK issue #1020 -- streaming + tool calling on Vertex AI loses tool input parameters. Workaround: use `stream=False` for requests with tools, `stream=True` for text-only. Monitor for upstream fix.

### Expected Features

**Must have (table stakes):**
- API key auth on `/mcp` endpoint with SHA-256 hashed storage and timing-safe comparison
- SA token auth for cluster-internal RCARS calls (re-read per request, never cache)
- `ph_rcars_query` tool with async poll-and-wait pattern (120s timeout, 3s poll interval)
- Express project DB model with JSONB intake data and phase tracking
- Conversational intake for express mode (reuse existing skill with routing branch)
- Manual environment gate for express ("order this CI, come back with credentials")
- One-directional Jira sync (PH pushes state, Jira is read-only view)
- Streaming chatbot responses via SSE
- Conversation persistence in portal DB (Anthropic API is stateless, PH owns history)
- Tool call visibility in chatbot UI (users see "Searching RCARS catalog..." not a blank screen)

**Should have (differentiators):**
- Per-key rate limiting with observability (start with generous limits, tighten based on usage)
- Session continuity across CC restarts via `ph_store_intake_results` / `ph_get_intake_results`
- Orchestrator MCP awareness (check local manifest, then portal, then new intake)
- Health check endpoint (`/health` with backend status)
- Human-in-the-loop approval for destructive chatbot actions
- Jira comments on phase transitions with portal links

**Defer (v2+):**
- Babylon ordering automation (manual gate works, CLI contract unstable)
- Express skill (cluster customization agent -- separate brainstorm+spec)
- OAuth 2.1 for MCP endpoint (overkill for <20 users, plan migration path)
- Bi-directional Jira sync (documented anti-pattern, never build)
- `oc` CLI in chatbot container (defer until express skill is ready)
- Multi-project context switching in chatbot (start with single-project sessions)

### Architecture Approach

The architecture follows a single-gateway pattern: the FastAPI portal backend IS the MCP gateway. FastMCP is mounted at `/mcp` on the existing app. Every external service (RCARS, Jira, Anthropic API) gets a service client class in `app/services/` with retry logic, timeout handling, and structured error responses. MCP tools delegate to these clients and never make HTTP calls directly. The chatbot proxy calls the same Python tool functions internally (no network hop), and the tool definitions for the Anthropic API are derived programmatically from the FastMCP tool registry.

**Major components:**
1. **PH MCP Server** -- Unified tool gateway for CC users. API key auth via FastMCP `Middleware.on_call_tool`. External HTTPS route for `/mcp` only.
2. **RCARS HTTP Client** -- Async client wrapping submit-query/poll-result lifecycle. SA token read per-request from filesystem.
3. **Express State Manager** -- Separate `ExpressProject` model (not overloading existing `Project`). JSONB for flexible data. Portal DB is source of truth for express only.
4. **Jira Client** -- Wraps `atlassian-python-api`. Runtime custom field resolution (query `/rest/api/2/field` on first call, cache with daily refresh). One-directional push.
5. **Chatbot Proxy** -- SSE endpoint at `/api/v1/chat`. Tool-use loop with direct function calls. Conversation history in portal DB keyed by session ID and user email.
6. **Ansible Deployer** -- All K8s resources (routes, secrets, config) managed via Ansible. No manual `oc edit`.

### Critical Pitfalls

1. **FastMCP mount path double-prefix** -- Mounting at `/mcp` with default path creates `/mcp/mcp`. Fix: use `mcp.http_app(path="/")` when mounting at a prefix, and use `combine_lifespans()` to merge portal + MCP lifespans. Both must be done in Phase 1 before any tool testing.

2. **CORS middleware collision** -- The existing top-level `CORSMiddleware` conflicts with FastMCP's internal CORS handling, producing duplicate headers and blocked preflights. Fix: remove top-level CORS, apply CORS middleware separately to each sub-app via the `middleware` parameter.

3. **Bound SA token expiration** -- OpenShift 4.11+ tokens expire after 1 hour. Reading the token once at startup causes all RCARS calls to fail silently after 1 hour. Fix: re-read from filesystem on every request. The file read is negligible compared to the HTTP call.

4. **MCP tool timeout on RCARS polling** -- FastMCP has a documented issue where tools exceeding ~5 seconds fail silently (issue #2845). RCARS queries take 20-60 seconds. Fix: set explicit `timeout=180` on the tool definition, send progress notifications during polling, implement graceful degradation.

5. **Timing-vulnerable API key comparison** -- Using `==` for hash comparison leaks timing information. Fix: always use `hmac.compare_digest()`. Single-line fix that prevents a category of attack. Non-negotiable.

6. **Cross-namespace NetworkPolicy blocking** -- DNS resolution does not imply connectivity. Fix: verify NetworkPolicies in both namespaces before writing integration code. Add connectivity smoke test to Ansible deploy playbook.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: RCARS MCP Gateway
**Rationale:** Foundation phase -- every other capability depends on the MCP gateway being deployed, authenticated, and functional. The RCARS integration also fixes the currently broken intake vetting (broken since RCARS v2 migration).
**Delivers:** Authenticated external MCP endpoint, RCARS query/catalog tools, fixed intake vetting, health check endpoint.
**Addresses:** API key auth middleware, SA token auth, RCARS HTTP client, cross-namespace connectivity, external Route via Ansible, intake skill update (replace broken curl with MCP tool reference).
**Avoids:** Pitfalls 1-9 (mount path, CORS, lifespan, auth mismatch, timing-safe comparison, tool timeout, NetworkPolicy, auth-delegator, token expiration). All nine critical pitfalls concentrate in this phase.
**Cross-repo work:** `rhdp-publishing-house-portal` (RCARS client + MCP tools), `rcars-advisory` (SA token auth middleware + SA allowlist), `rhdp-publishing-house-skills` (intake skill update).

### Phase 2: Express Mode Framework
**Rationale:** Express mode needs both the MCP gateway (Phase 1) and RCARS tools for vetting/base-finding. The framework is useful without the express skill -- users can track express projects and store artifacts even before the customization agent exists.
**Delivers:** Express project DB model, express MCP tools, orchestrator MCP awareness, session continuity, portal express views (kanban cards, detail view, artifact viewer), three-mode intake selection.
**Addresses:** Express DB model with JSONB, `ph_create_express_project` / `ph_update_express_status` / `ph_store_express_artifact` tools, manual environment gate, recap document generation.
**Avoids:** Pitfall 10 (express state divergence) -- design the artifact storage and session-resume assessment from the start.

### Phase 3: Jira Integration
**Rationale:** Independent of express mode but benefits from MCP gateway patterns being proven. Starts with brainstorm+spec to resolve ticket structure, trigger points, and workflow mapping before building.
**Delivers:** Jira ticket creation on project events, phase transition status updates, Jira comments with portal links, Jira issue key in manifest/portal record.
**Addresses:** `ph_jira_create_issue` / `ph_jira_link_project` / `ph_jira_get_issue` tools, one-directional sync contract, runtime custom field resolution.
**Avoids:** Pitfall 11 (Jira custom field opacity) -- resolve fields by name at runtime, never hardcode IDs. Anti-pattern: bi-directional sync.

### Phase 4: Portal Chatbot
**Rationale:** Depends on MCP gateway and benefits from express framework being in place (more tools available). Most complex phase from a UX perspective. Starts with brainstorm+spec.
**Delivers:** SSE streaming chatbot, tool call visibility, conversation persistence, abort/cancel control, same MCP tool access as CC users.
**Addresses:** Anthropic SDK integration, SSE streaming via `sse-starlette`, PatternFly ChatBot components, tool-use loop with direct function dispatch, conversation history in portal DB.
**Avoids:** Pitfall 12 (streaming messages lost on disconnect) -- persist messages to DB as they are emitted, not just at end of conversation. Anti-patterns: LangChain, separate tool registry, general-purpose chat UI.

### Phase Ordering Rationale

- **MCP gateway must be first** because CC users need authenticated MCP access for RCARS tools, and both express mode and chatbot consume those tools.
- **Express framework second** because it depends on RCARS vetting tools and proves the orchestrator MCP awareness pattern that benefits all modes.
- **Jira third** because it is independent of express but benefits from the service client abstraction pattern established in Phases 1-2. Starting with brainstorm+spec means design work can overlap with Phase 2 build work.
- **Chatbot last** because it reuses all MCP tools from Phases 1-3, and shipping it last means every tool it needs already exists and is tested.
- **Jira and chatbot brainstorm/spec can run in parallel** with earlier phase implementation work. The research identifies the key decisions each brainstorm must resolve (listed in Gaps to Address below).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (RCARS Gateway):** Needs `/gsd-research-phase` for FastMCP 3.x middleware patterns specifically -- the upgrade from 2.0 to 3.2+ changes the auth implementation approach. Also needs validation of RCARS SA token auth (which is specified but not yet implemented in the RCARS repo).
- **Phase 3 (Jira Integration):** Needs brainstorm to resolve Jira ticket structure, trigger points, and whether to use `atlassian-python-api` directly or evaluate the official Atlassian Remote MCP Server for read-only queries.
- **Phase 4 (Portal Chatbot):** Needs brainstorm to resolve execution model (direct Anthropic SDK tool-use loop vs. Claude Agent SDK), Vertex AI streaming+tools bug workaround strategy, and chatbot user auth model.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Express Framework):** DB model, Alembic migrations, MCP tool registration, portal React views -- all well-documented patterns already used in the existing codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified against PyPI/npm. Versions pinned to current stable releases. FastMCP 3.2.4 middleware docs verified via Context7. Known issue documented for Vertex AI streaming+tools. |
| Features | MEDIUM-HIGH | Strong for MCP gateway and express mode (completed design specs). Medium for Jira and chatbot (brainstorm-only status). Feature dependency chain is clear and validated. |
| Architecture | HIGH | Single-gateway pattern is well-documented across MCP ecosystem. Component boundaries match existing codebase patterns. Separate `ExpressProject` model avoids overloading existing schema. |
| Pitfalls | HIGH | 12 pitfalls documented with specific code fixes, warning signs, and phase mapping. All critical pitfalls verified against official docs (Context7 for FastMCP, K8s docs for SA tokens, Atlassian docs for Jira). |

**Overall confidence:** MEDIUM-HIGH

The MCP gateway and express framework phases (1-2) have HIGH confidence -- design specs exist, patterns are documented, and pitfalls have known solutions. The Jira and chatbot phases (3-4) have MEDIUM confidence because they are still at brainstorm stage and key design decisions (ticket structure, execution model, auth model) are unresolved.

### Gaps to Address

- **RCARS SA token auth implementation:** The `RCARS_SA_ALLOWLIST_STR` config field exists in RCARS but is not yet wired into the auth middleware. This is a cross-repo dependency that must be resolved before Phase 1 integration testing.
- **Jira Cloud vs. Data Center:** The research references both `issues.redhat.com` (likely Data Center) and Cloud patterns. Auth differs significantly (PAT with Bearer auth for Data Center vs. basic auth with API token for Cloud). Must confirm which Jira instance PH targets before Phase 3.
- **Jira ticket structure:** One epic per project with comments, or epic + subtasks per phase? Needs brainstorm with the team.
- **Chatbot execution model:** Direct Anthropic SDK tool-use loop (recommended by STACK research) vs. Claude Agent SDK (referenced in FEATURES research). The STACK research makes a strong case for the direct SDK approach (~50 lines of code, no framework overhead). The FEATURES research references the Agent SDK but does not argue against the direct approach.
- **Chatbot user auth model:** How do chatbot users authenticate to PH? OAuth proxy headers provide user identity, but tool-level authorization (which tools can chatbot users invoke?) is not yet designed.
- **Vertex AI streaming+tools bug:** Anthropic SDK issue #1020 affects chatbot UX. The workaround (disable streaming for tool-use requests) is functional but degrades the experience. Monitor for upstream fix before Phase 4 implementation.
- **CORS middleware refactoring scope:** Moving from top-level `CORSMiddleware` to per-sub-app CORS requires changes to existing API route middleware. Must be tested against the portal frontend to ensure no regression.

## Sources

### Primary (HIGH confidence)
- FastMCP 3.2.4 docs (Context7 verified): middleware, HTTP deployment, dependency injection, auth patterns
- Anthropic Python SDK v0.97.0: PyPI, GitHub, Vertex AI docs
- PatternFly ChatBot v6.4.1: npm registry, official docs, React 19 support confirmed
- Kubernetes docs: ServiceAccount tokens, TokenReview API, NetworkPolicy
- OpenShift docs: Bound service account tokens, Route TLS termination
- FastMCP GitHub issues: #2845 (tool timeout), #2817 (combined app auth), #2139 (CORS), MCP SDK #1367 (mount path)

### Secondary (MEDIUM confidence)
- atlassian-python-api v4.0.7: PyPI, ReadTheDocs (Jira Cloud auth, `enhanced_jql`)
- sse-starlette: PyPI (version not pinpointed)
- Anthropic SDK issue #1020: Vertex AI streaming+tools bug (open, community fix exists)
- MCP gateway pattern guides: ChatForest, Gravitee, Traefik Hub, Stainless

### Tertiary (LOW confidence -- needs validation)
- Jira Data Center PAT auth patterns (PH Jira instance type unconfirmed)
- Express project abandonment policy thresholds (no prior art in PH codebase)
- Chatbot container strategy for `oc` CLI (deferred, no design spec)

---
*Research completed: 2026-04-30*
*Ready for roadmap: yes*
