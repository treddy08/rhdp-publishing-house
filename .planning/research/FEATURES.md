# Feature Landscape

**Domain:** AI-powered content lifecycle management platform -- MCP gateway integrations, express provisioning, Jira-connected pipelines, AI chatbot interfaces
**Researched:** 2026-04-30
**Overall Confidence:** MEDIUM-HIGH (strong for MCP gateway and express mode due to completed design specs; medium for Jira and chatbot due to brainstorm-only status)

---

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy.

### MCP Server Gateway

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| API key authentication on `/mcp` endpoint | Any externally-routed MCP server without auth is an open door to backend services. Users and admins expect credentials to be required. | Low | Design spec already covers this: Bearer token in header, SHA-256 hashed storage in K8s Secret, timing-safe comparison. Follow the pattern exactly. |
| Scoped auth middleware (MCP routes only) | Internal portal APIs (`/api/v1/projects`, etc.) must remain cluster-internal. Exposing everything through the external route is a security failure. | Low | Route only `/mcp` externally. Middleware checks API key only on `/mcp` paths. |
| Graceful error handling for backend unavailability | If RCARS is down or slow, the MCP tool must return a structured error the skill can handle -- not hang, crash, or return raw HTTP errors. | Med | Poll-with-timeout pattern for async RCARS queries (120s timeout, 3s poll interval per spec). On timeout or 5xx, return `{"error": "rcars_unavailable", "message": "..."}`. Skill decides how to proceed. |
| Tool-level documentation (descriptions, parameter schemas) | MCP clients (Claude Code, Cursor) display tool descriptions to the model. Poor descriptions = poor tool selection = broken agent behavior. | Low | FastMCP 2.0 `@mcp.tool` decorator supports docstrings and type hints that auto-generate schemas. Write them carefully -- they are part of the user experience even though users never see them directly. |
| Cross-namespace service discovery | PH backend must reach RCARS via K8s service DNS (`rcars-api.rcars-dev.svc.cluster.local:8080`). If this doesn't work, nothing works. | Low | Standard K8s pattern. Verify no NetworkPolicies block cross-namespace traffic in either namespace. |
| SA token auth for cluster-internal calls | PH must authenticate to RCARS using its auto-mounted ServiceAccount token. No manual secret creation or rotation. | Low | K8s handles token lifecycle. RCARS validates via TokenReview API. Add PH SA to RCARS allowlist in Ansible vars. |
| HTTPS with TLS termination on external route | External MCP traffic must be encrypted. API keys over plain HTTP is a non-starter. | Low | OpenShift Route with `tls.termination: edge`. Already standard for all RHDP routes. |

### Express Mode Provisioning

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Conversational intake capturing requirements | Users need to describe what they need in natural language. The intake skill already does this for onboarded/self-published modes -- express must match that experience. | Low | Reuse existing intake skill with a new routing branch for express. The interview flow is the same; only the downstream actions differ. |
| RCARS vetting query (overlap detection) | Before building anything, check if it already exists. Same value prop as for all modes -- reuse is always better than new work. | Low | Same `ph_rcars_query` MCP tool. The express intake sends the same kind of query text; the tool is the same pipe. |
| Portal DB state for express projects | Express projects have no git repo. State must persist somewhere. The portal DB is the only option. | Med | New `express_projects` and `express_artifacts` tables. JSONB for flexible intake data storage. Standard SQLAlchemy model + Alembic migration. |
| Phase tracking (intake -> environment -> customize -> complete) | Users need to know where they are. The portal needs to show progress. Without phase tracking, express projects are invisible black boxes. | Low | Enum field on the express project model. Updated via `ph_update_express_status` MCP tool. |
| Manual environment gate (user provisions, returns with credentials) | The environment must exist before customization can start. Even without Babylon ordering automation, the gate pattern works -- PH tells the user what to order and waits. | Low | Conversational gate: "Order CI X, run `oc login`, come back when ready." Agent checks `oc whoami` to verify. |
| Recap document generation and storage | The user needs to know what was done, what's left, and how to use what was built. This is the primary deliverable of express mode. | Med | Agent logs all actions during customization. Recap is a structured markdown doc stored in portal DB via `ph_store_express_artifact`. Local CC users also get a file copy. |
| Express projects visible in portal UI | If express projects don't show up alongside full projects, users with multiple projects lose track. The portal is the multi-project dashboard. | Med | Express cards on the kanban board (distinct visual style). Express detail view showing intake data, base CI, phase, artifacts. Filter/toggle on project list. |

### Jira Integration

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Create Jira tickets from PH project events | This is the core ask: when a PH project reaches a milestone (intake complete, review needed, published), a Jira ticket should reflect that state. Without this, the integration has no purpose. | Med | Use the Atlassian MCP server (official, remote, OAuth/API-token auth) or wrap Jira REST API via PH MCP tools. The Atlassian MCP server supports creating issues with `create_issue` tool. |
| Manifest remains source of truth | Jira is a mirror, not the authority. If someone edits Jira directly, PH should not break. The git manifest (for onboarded/self-published) or portal DB (for express) is always authoritative. | Low | One-directional sync for state: PH -> Jira. Jira edits are informational only. PH overwrites Jira state on next sync. Document this clearly so users understand the contract. |
| Link PH project to Jira epic/ticket | A PH project should map to a Jira tracking structure. Users need to find their PH project in Jira and vice versa. | Low | Store Jira issue key in manifest (`jira.epic_key`) and/or portal DB. PH creates the link during intake or on first Jira sync. |
| Update Jira ticket status on phase transitions | When PH moves from writing to editing, the Jira ticket should reflect "In Review" (or similar). This keeps stakeholders informed without requiring them to use PH or the portal. | Med | Map PH phases to Jira workflow transitions. Use `transition_issue` via Atlassian MCP server or Jira REST API. Handle cases where the Jira workflow doesn't match PH phases (log a warning, don't fail). |

### Portal Chatbot

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Streaming text responses | Users expect to see the AI "thinking" as tokens arrive, not wait for complete responses. Every modern AI chat UI streams. Without it, the chatbot feels broken during long generations. | Med | SSE from backend to React frontend. Use `@anthropic-ai/claude-agent-sdk` with `includePartialMessages: true` for incremental text + tool call events. React frontend renders deltas in real-time. |
| Conversation persistence across sessions | If a user closes their browser and returns, their conversation should be there. Losing context is a deal-breaker for a tool that manages multi-day workflows. | Med | Store conversation history in portal DB (or use Claude Managed Agents which persists session history server-side). Load on reconnect. Session ID in URL or user identity mapping. |
| Tool call visibility | When the chatbot calls `ph_rcars_query` or `ph_create_express_project`, the user should see what's happening -- not a blank screen. This builds trust and helps users understand the system. | Med | Render tool call start/complete events inline in the chat. Show tool name and a brief description ("Searching RCARS catalog..."). Don't show raw JSON parameters unless the user asks. |
| Abort/cancel control | Users must be able to stop a runaway generation or cancel an operation that's taking too long. | Low | Frontend `stop()` control that cancels the SSE stream. Backend respects cancellation. Standard pattern in Vercel AI SDK and assistant-ui. |
| Same capabilities as local CC | The chatbot is the access path for users without Claude Code. If it can do less than local CC, it's a second-class experience. Feature parity is the goal. | High | This is the hardest requirement. The chatbot must access the same MCP tools, run the same skill logic, and produce the same outputs. Architecture: chatbot backend runs the Agent SDK (or a Claude API agentic loop) with the same MCP server configuration as local CC users. |

---

## Differentiators

Features that set the product apart. Not expected, but valuable.

### MCP Server Gateway

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-key rate limiting with observability | Prevents runaway agents from exhausting RCARS or backend services. Provides usage data for capacity planning. Most MCP servers in production lack this. | Med | Implement token-bucket or sliding-window rate limiting per API key. Log rate-limit events. Start with generous limits (100 req/min per key) and tighten based on observed usage. JSON-RPC error response with `retryAfter` in error data. |
| Hot-reload API key Secret | Add/revoke API keys without pod restart. Admin experience improvement -- especially valuable when onboarding new CC users or revoking compromised keys. | Med | K8s Secret volume mount with `inotify` watch, or periodic re-read (every 60s). FastAPI startup event loads initial keys; background task refreshes. If too complex, accept pod restart for now -- the admin experience is "run deployer, wait 30s." |
| MCP tool usage analytics | Track which tools are called, how often, by which key, with what latency. Feeds into understanding how PH is actually used. | Med | Structured logging per tool call: `{tool, key_name, latency_ms, status, timestamp}`. Prometheus metrics optional but valuable. Start with structured logs, add Grafana later. |
| Unified gateway for future backends | The same MCP server pattern (`ph_<service>_<action>`) extends naturally to Jira, Babylon, and any future backend. Skills never learn new integration patterns. | Low | This is already designed into the architecture. Each backend gets its own set of MCP tools. The gateway handles auth and routing for all of them. Document the naming convention and tool contract pattern. |
| Health check endpoint | Load balancers and monitoring systems can verify the MCP server is alive and its backends are reachable. | Low | `/health` endpoint that checks: (1) MCP server is responding, (2) RCARS is reachable, (3) portal DB is connected. Return `{"status": "healthy", "backends": {"rcars": "ok", "db": "ok"}}`. |

### Express Mode Provisioning

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| RCARS base-finding query (infrastructure matching) | Instead of the user guessing which CI to order, RCARS finds the closest base infrastructure. Dramatically reduces the "what do I order?" friction. | Med | Second `ph_rcars_query` call with a broader, infrastructure-focused query. Works as content-analysis proxy until RCARS gets infrastructure-aware metadata (RCARS backlog item). Imperfect but functional. |
| Session continuity across CC restarts | User starts intake in one CC session, clones a repo, opens a new CC session, and PH picks up where they left off. No context lost. | Med | `ph_store_intake_results` and `ph_get_intake_results` MCP tools. Orchestrator checks portal for in-progress projects by user email before starting fresh intake. Works for all modes, not just express. |
| Lightweight Showroom guide from express customization | After customizing an environment, optionally generate a brief Showroom-style guide documenting what was built. Turns a throwaway environment into something someone else could follow. | Med | Comes at the end of Phase 4 (Handoff). Agent generates AsciiDoc from the recap log. Not a full lab -- more like a "quick start" doc. Stored as an artifact in portal DB. |
| Orchestrator MCP awareness | Orchestrator discovers projects from portal via MCP before falling back to local manifest. Enables multi-device, multi-session workflows. | Med | New orchestrator startup flow: (1) check CWD for manifest, (2) query `ph_list_projects` via MCP, (3) start new intake. This benefits all modes, not just express. |
| Express project lifecycle management (abandonment policy) | Mark stale express projects as "abandoned" so they don't clutter the portal forever. | Low | Cron job or manual admin action. Projects in "in_progress" for >30 days get flagged. No auto-delete -- just a status change and visual indicator. |

### Jira Integration

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Automatic Jira comment on phase transitions | Every PH phase transition adds a Jira comment with a brief summary ("Writer completed module 3 of 5. Editor review next."). Stakeholders get a running log without leaving Jira. | Low | Use `add_comment` via Atlassian MCP server on each phase transition. Template the comment text. Include a link to the portal project view if portal registration exists. |
| Jira ticket structure reflecting PH phases | One epic per PH project, with subtasks per phase. Gives Jira-native teams a familiar structure to track progress. | Med | Create epic on project init. Create subtasks for each phase as the project enters them. Close subtasks on phase completion. Handle the case where Jira workflows vary by project -- use a configurable phase-to-status mapping. |
| Conflict-safe one-directional sync | PH pushes state to Jira but never reads Jira state as authoritative. If someone edits a Jira ticket directly, PH's next push overwrites it. No sync loops, no conflict resolution needed. | Low | This is a deliberate simplification. Bi-directional sync with Jira is a well-documented source of bugs (duplicate creation, comment loops, status oscillation). Avoid it entirely. PH is the source of truth. Jira is the view. |
| Configurable Jira project/board targeting | Different PH projects may map to different Jira projects. The mapping should be configurable per PH project, not hardcoded globally. | Low | Store Jira project key in the PH manifest or portal project record. Default from a global config; override per project. |
| Jira labels/custom fields for PH metadata | Tag Jira tickets with PH-specific metadata: deployment mode, products covered, target audience. Enables Jira-native filtering and reporting. | Low | Map manifest fields to Jira labels or custom fields. Custom fields require Jira admin setup -- document the requirements. Labels are simpler and work without admin changes. Start with labels. |

### Portal Chatbot

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Human-in-the-loop approval for destructive actions | Before the chatbot agent runs `oc delete` or creates a Jira epic, it asks the user for confirmation. Prevents accidental damage and builds trust. | Med | AG-UI pattern: agent emits a `TOOL_CALL_ARGS` event, frontend shows an approval dialog, user confirms or rejects, agent proceeds or aborts. Critical for express mode where the agent runs real `oc` commands. |
| Thinking/reasoning visibility | Show the user what the agent is reasoning about before it acts. Separates internal reasoning from public responses. | Low | Use Claude's extended thinking feature. Stream thinking blocks separately from response blocks. Frontend renders them in a collapsible "Thinking..." section. |
| Express mode `oc` execution from chatbot | Chatbot users need to customize environments just like local CC users. The chatbot container must have `oc` CLI and cluster credentials. | High | Bake `oc` into the chatbot container image. For each express session, the user provides cluster credentials (API URL + token). Agent uses `oc login` to authenticate. Security: credentials must not persist beyond the session. |
| Multi-project context switching | Chatbot users may have multiple PH projects (some express, some onboarded). The chatbot should let them switch between projects without losing context. | Med | Project selector in the chatbot UI. Each project gets its own conversation thread. Switching projects loads the relevant context (manifest, intake data, phase state). |
| Inline artifact rendering | When the agent generates a recap document or a vetting report, render it inline in the chat with proper formatting (markdown, code blocks, tables). Don't force the user to download a file. | Low | Standard markdown rendering in the chat component. assistant-ui and similar libraries handle this natively. For longer artifacts, render a preview with a "View full document" expansion. |

---

## Anti-Features

Features to explicitly NOT build. These are tempting but harmful.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Bi-directional Jira sync | Bi-directional sync with Jira is a well-documented source of production bugs: duplicate ticket creation, comment sync loops, status oscillation, and conflict resolution complexity. ServiceNow-to-Jira, Bugcrowd-to-Jira, and Jira-to-Jira integrations all document these exact failure modes. The ROI of bi-directional sync is not worth the maintenance burden for an internal tool. | One-directional push: PH -> Jira. PH is the source of truth. Jira is a read-only view for stakeholders. If someone edits Jira directly, PH's next push overwrites it. Document this contract clearly. |
| OAuth 2.1 for MCP endpoint (this milestone) | OAuth adds discovery endpoints, token exchange, PKCE, refresh flows, and a browser-based auth dance. For an internal team of <20 users, API keys are simpler, sufficient, and already designed. OAuth is the right move when PH goes multi-tenant or public -- not now. | API keys in K8s Secret. SHA-256 hashed storage. Bearer token in header. Plan the migration path to OAuth 2.1 for a future milestone if PH goes beyond the internal team. |
| Babylon ordering automation (this milestone) | The Babylon CLI contract (exact command syntax, response format, credential format) is not fully specified. Building automation against an unstable interface means rework. The manual gate ("order this CI, come back with credentials") works and is well-understood. | Manual gate for environment provisioning. User orders the CI themselves and returns with credentials. PH validates with `oc whoami`. Automate in a future milestone once the Babylon CLI contract stabilizes. |
| Full-blown ChatGPT-style chatbot UI | Building a general-purpose AI chat UI with conversation branching, message editing, fork-and-compare, persona switching, and prompt libraries is massive scope. PH's chatbot is a tool for a specific workflow, not a general AI assistant. | Purpose-built chat UI focused on PH workflows: intake conversation, express provisioning, project status queries, artifact viewing. Use assistant-ui or a similar component library for the chat shell, but don't build features that don't serve PH use cases. |
| Direct skill execution in chatbot (skip MCP) | If the chatbot calls backend APIs directly instead of going through MCP tools, you create two code paths -- one for CC users (MCP) and one for chatbot users (direct). Every feature needs to be built and tested twice. | Chatbot backend uses the same MCP tools as CC users. The Agent SDK calls `ph_rcars_query`, `ph_create_express_project`, etc. through the MCP server. One code path, one set of tools, one integration surface. |
| Real-time collaboration / shared editing | Multi-user real-time editing on the same PH project introduces operational transform or CRDT complexity that is completely disproportionate to the use case. PH projects are typically single-author with async handoffs. | Git-based async handoffs. Manifest + worklog in git handles multi-person workflows. Portal shows project state to all stakeholders. Worklog captures decisions and handoff notes. |
| Express skill in this milestone | The express skill (the agent that actually customizes OpenShift clusters) is a substantial piece of agent engineering -- its own brainstorm, spec, and implementation. Bundling it with the express framework would delay the entire milestone. | Build the express framework first (DB model, MCP tools, orchestrator awareness, portal views). Ship the express skill as a separate workstream. The framework is useful without the skill -- users can still track express projects and store artifacts manually. |
| Portal as primary state store (replacing git manifest) | Moving the source of truth from git to the portal DB creates a single point of failure, loses offline capability, and breaks the "CC works without portal" contract. | Git manifest stays the source of truth for onboarded/self-published. Portal DB is the source of truth only for express projects (which have no git repo by design). Portal is a cache/view for git-backed projects. |

---

## Feature Dependencies

```
RCARS Integration (MCP Gateway)
    |
    +-- ph_rcars_query tool
    |       |
    |       +-- Express Mode (uses ph_rcars_query for vetting + base-finding)
    |       +-- Intake Skill update (replaces broken curl call)
    |
    +-- API key auth middleware
    |       |
    |       +-- External MCP route (CC users connect)
    |       +-- Portal chatbot (uses same auth internally or via SA token)
    |
    +-- SA token auth to RCARS
            |
            +-- All RCARS MCP tools depend on this

Express Mode Framework
    |
    +-- Portal DB model for express projects
    |       |
    |       +-- Express portal views (kanban, detail, artifact viewer)
    |       +-- Express MCP tools (ph_create_express_project, etc.)
    |
    +-- Orchestrator MCP awareness
    |       |
    |       +-- Session continuity (all modes benefit)
    |       +-- Express project discovery
    |
    +-- Environment gate (manual initially)
            |
            +-- Express skill (separate, later) -- depends on environment being ready

Jira Integration
    |
    +-- Atlassian MCP server connectivity (or PH-wrapped Jira REST API tools)
    |       |
    |       +-- ph_jira_create_issue tool
    |       +-- ph_jira_update_status tool
    |       +-- ph_jira_add_comment tool
    |
    +-- Jira project/ticket mapping in manifest/portal
    |
    +-- Phase transition hooks (orchestrator fires Jira updates)
    |
    (Independent of RCARS integration, but benefits from MCP gateway being established)

Portal Chatbot
    |
    +-- MCP gateway deployed + external route (required)
    |       |
    |       +-- Chatbot backend uses MCP tools just like CC users
    |
    +-- Claude Agent SDK or Claude API agentic loop (backend)
    |       |
    |       +-- Streaming responses via SSE to frontend
    |       +-- Tool call events forwarded to UI
    |
    +-- React chat component (frontend)
    |       |
    |       +-- assistant-ui or custom component
    |       +-- SSE consumer for streaming
    |
    +-- Conversation persistence (portal DB)
    |
    +-- oc CLI in container image (for express mode)
    |
    (Depends on MCP gateway + express framework being in place)
```

### Critical Path

```
1. RCARS Integration (MCP Gateway)  -- no dependencies, enables everything else
2. Express Mode Framework            -- depends on MCP gateway
3. Jira Integration                  -- independent, but benefits from MCP gateway patterns
4. Portal Chatbot                    -- depends on MCP gateway + express framework
```

---

## MVP Recommendation

### Phase 1: RCARS MCP Gateway (foundation)

Prioritize:
1. API key auth middleware on `/mcp` route
2. SA token auth to RCARS (cross-namespace)
3. `ph_rcars_query` tool (async polling, structured results)
4. `ph_rcars_catalog_search` and `ph_rcars_catalog_item` tools
5. External route deployment via Ansible
6. Intake skill update (replace broken curl with MCP tool reference)
7. Health check endpoint

Defer: Per-key rate limiting (add after observing real usage), hot-reload API keys (pod restart is fine initially), usage analytics (start with structured logs).

### Phase 2: Express Mode Framework (third deployment mode)

Prioritize:
1. Express project DB model + Alembic migrations
2. Express MCP tools (`ph_create_express_project`, `ph_update_express_status`, `ph_store_express_artifact`, `ph_get_express_project`)
3. Orchestrator MCP awareness (check local -> portal -> new intake)
4. Intake mode selection (three modes, user picks)
5. Session continuity MCP tools (`ph_store_intake_results`, `ph_get_intake_results`)
6. Manual environment gate
7. Portal express views (kanban cards, detail view, artifact viewer)

Defer: Express skill (separate workstream), Babylon ordering automation (manual gate works), RCARS infrastructure-aware metadata (RCARS backlog), express project abandonment policy.

### Phase 3: Jira Integration (stakeholder visibility)

Prioritize:
1. Atlassian MCP server connectivity (or PH-wrapped Jira REST API)
2. `ph_jira_create_issue` MCP tool
3. Jira epic creation on project init
4. Phase transition -> Jira status update
5. Jira comment on phase transitions
6. Jira project key in manifest/portal record

Defer: Subtask-per-phase structure (start with epic + comments, evolve if needed), custom fields (start with labels), configurable phase-to-status mapping (start with a sensible default).

### Phase 4: Portal Chatbot (access democratization)

Prioritize:
1. Claude Agent SDK backend with MCP tool access
2. SSE streaming to React frontend
3. Chat component (assistant-ui or custom)
4. Tool call visibility (inline indicators)
5. Conversation persistence
6. Abort/cancel control

Defer: Human-in-the-loop approval (add after basic tool calling works), `oc` in container (add when express skill is ready), multi-project context switching (start with single-project sessions), thinking visibility.

---

## Sources

### MCP Gateway Patterns
- [MCP Gateway & Proxy Patterns -- ChatForest](https://chatforest.com/guides/mcp-gateway-proxy-patterns/) -- HIGH confidence (comprehensive pattern catalog)
- [MCP API Gateway Explained -- Gravitee](https://www.gravitee.io/blog/mcp-api-gateway-explained-protocols-caching-and-remote-server-integration) -- HIGH confidence
- [MCP Server API Key Management Best Practices -- Stainless](https://www.stainless.com/mcp/mcp-server-api-key-management-best-practices) -- HIGH confidence
- [Securing Your MCP Server with API Key Authentication -- CodeSignal](https://codesignal.com/learn/courses/advanced-mcp-server-and-agent-integration-in-python/lessons/securing-your-mcp-server-with-api-key-authentication-in-fastapi) -- MEDIUM confidence
- [MCP Server Rate Limiting: Implementation Guide -- Fast.io](https://fast.io/resources/mcp-server-rate-limiting/) -- MEDIUM confidence
- [MCP Server Observability -- Zeo](https://zeo.org/resources/blog/mcp-server-observability-monitoring-testing-performance-metrics) -- MEDIUM confidence
- [HTTP Deployment -- FastMCP](https://gofastmcp.com/deployment/http) -- HIGH confidence (official docs)
- [MCP Gateway Best Practices -- Traefik Hub](https://doc.traefik.io/traefik-hub/mcp-gateway/guides/mcp-gateway-best-practices) -- HIGH confidence

### Express / Disposable Provisioning
- [Disposable Cloud Environments -- BeCloudReady](https://www.becloudready.com/post/what-are-disposable-cloud-environments-and-why-do-you-need-them) -- MEDIUM confidence
- [Disposable Cloud Resources -- Instruqt](https://instruqt.com/blog/why-tech-vendors-should-use-disposable-cloud-resources-for-sales-demos-and-tech-training) -- MEDIUM confidence
- [OpenShift Demos & Workshops -- RHPDS](https://demo.openshift.com/) -- HIGH confidence (internal Red Hat platform)

### Jira Integration
- [Atlassian Remote MCP Server -- GitHub](https://github.com/atlassian/atlassian-mcp-server) -- HIGH confidence (official Atlassian)
- [Introducing Atlassian Remote MCP Server -- Atlassian Blog](https://www.atlassian.com/blog/announcements/remote-mcp-server) -- HIGH confidence (official)
- [Jira Content Management Template -- Atlassian](https://www.atlassian.com/software/jira/templates/content-management) -- MEDIUM confidence
- [Jira Webhooks Guide -- Inventive](https://inventivehq.com/blog/jira-webhooks-guide) -- MEDIUM confidence
- [ServiceNow-Jira Bi-directional Webhooks -- ServiceNow Community](https://www.servicenow.com/community/developer-articles/a-practical-use-for-setting-up-jira-to-servicenow-bi-directional/ta-p/3160262) -- MEDIUM confidence (anti-pattern evidence)

### Portal Chatbot / AI Agent UI
- [AG-UI Protocol -- Docs](https://docs.ag-ui.com/introduction) -- HIGH confidence (protocol spec)
- [assistant-ui](https://www.assistant-ui.com/) -- HIGH confidence (production library)
- [Claude Agent SDK Streaming -- Anthropic Docs](https://code.claude.com/docs/en/agent-sdk/streaming-output) -- HIGH confidence (official)
- [Hosting the Agent SDK -- Anthropic Docs](https://platform.claude.com/docs/en/agent-sdk/hosting) -- HIGH confidence (official)
- [Claude Managed Agents Overview -- Anthropic Docs](https://platform.claude.com/docs/en/managed-agents/overview) -- HIGH confidence (official)
- [LangChain Agent Chat UI -- GitHub](https://github.com/langchain-ai/agent-chat-ui) -- MEDIUM confidence
