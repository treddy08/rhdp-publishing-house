# Architecture Patterns

**Domain:** AI-powered content lifecycle management platform (MCP gateway, express provisioning, Jira integration, chatbot proxy)
**Researched:** 2026-04-30

---

## Recommended Architecture

The Publishing House milestone adds four new capability layers to the existing FastAPI + React + OpenShift system. Each layer builds on the previous one but has distinct component boundaries, data flows, and deployment concerns.

### System Overview

```
                                    EXTERNAL
                                    --------
    Claude Code user                Portal/chatbot user
         |                                |
    Bearer API key                   OAuth proxy (existing)
         |                                |
         v                                v
    +-----------------------------------------------+
    |  PH Portal Backend (FastAPI)                  |
    |  namespace: publishing-house-dev               |
    |                                               |
    |  /mcp -----> FastMCP server (streamable HTTP) |
    |               |-- ph_rcars_query              |
    |               |-- ph_rcars_catalog_search     |
    |               |-- ph_rcars_catalog_item       |
    |               |-- ph_list_projects            |
    |               |-- ph_create_express_project   |
    |               |-- ph_store_express_artifact   |
    |               |-- ph_jira_create_issue (later)|
    |               +-- (existing tools)            |
    |                                               |
    |  /api/v1 --> REST API (existing)              |
    |  /api/v1/chat --> Chatbot proxy (new)         |
    |                                               |
    |  Internal services:                           |
    |    RCARS client -----> SA token auth           |
    |    Jira client ------> API token auth          |
    |    LLM proxy --------> Anthropic API           |
    +-----------------------------------------------+
              |                    |
              v                    v
    +------------------+   +-----------------+
    | RCARS API        |   | Jira Cloud      |
    | rcars-dev ns     |   | (external SaaS) |
    | port 8080        |   |                 |
    +------------------+   +-----------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Auth Mechanism |
|-----------|---------------|-------------------|----------------|
| **PH MCP Server** | Unified tool gateway for CC users. Exposes all backend capabilities as MCP tools. | FastMCP middleware --> RCARS client, DB, Jira client | API key (Bearer header, SHA-256 hashed, K8s Secret) |
| **RCARS HTTP Client** | Internal service that wraps RCARS v2 API calls (submit query, poll result, catalog browse). Handles async job lifecycle. | RCARS API via cross-namespace K8s DNS | SA token (auto-mounted, TokenReview validation) |
| **Express State Manager** | DB layer for express project lifecycle. Stores intake data, phase tracking, artifacts as JSONB. No git repo, portal DB is source of truth. | PostgreSQL (existing PH DB) | Internal (no external auth) |
| **Jira Client** | Wraps Jira Cloud REST API for issue create/update/link. Manifest stays source of truth; Jira is a sync target, not the authority. | Jira Cloud REST API (external) | API token (Jira PAT or OAuth 2.0 App, K8s Secret) |
| **Chatbot Proxy** | WebSocket or SSE endpoint that accepts natural language, routes through LLM with MCP tool access, streams response back. Reuses the same MCP tools as CC users. | Anthropic API (LLM), PH MCP tools (internal), Portal DB | OAuth proxy (existing, user identity from headers) |
| **Portal REST API** | Existing project CRUD, refresh, worklog, validation. Gains express project endpoints. | PostgreSQL, GitHub API | Internal (cluster-only, OAuth proxy on frontend) |
| **Portal Frontend** | React UI. Gains express project views, chatbot widget, Jira ticket links. | Portal REST API, Chatbot WebSocket | OAuth proxy (existing) |
| **Ansible Deployer** | Infrastructure-as-code for all K8s resources. Manages secrets, routes, config, builds. No manual `oc edit`. | OpenShift API | kubeconfig (Ansible controller) |

---

## Data Flow

### Flow 1: CC User --> RCARS Vetting (MCP path)

This is the primary integration path and must work before anything else.

```
1. CC user invokes intake skill
2. Skill calls ph_rcars_query(query="...") via MCP
3. CC sends HTTPS POST to ph-mcp.apps.<cluster>/mcp
4. PH backend validates API key:
   a. Extract Bearer token from Authorization header
   b. SHA-256 hash it
   c. Compare against hashed keys in ph-mcp-api-keys Secret
   d. 401 if no match
5. FastMCP dispatches to ph_rcars_query tool handler
6. Tool handler calls RCARS HTTP client internally:
   a. Read SA token from /var/run/secrets/kubernetes.io/serviceaccount/token
   b. POST to http://rcars-api.rcars-dev.svc.cluster.local:8080/api/v1/advisor/query
      with Authorization: Bearer <sa-token>
      body: {query, stages: ["prod", "dev", "event"]}
   c. Receive {job_id}
7. Poll GET /api/v1/advisor/query/{job_id}/result every 3s, timeout 120s
8. Return structured results to MCP tool response
9. Skill receives results, writes vetting report
```

**Critical dependency:** RCARS must add SA token validation to its auth middleware. Currently RCARS only checks `X-Forwarded-Email` / `X-Forwarded-User` headers (OAuth proxy path). The `sa_allowlist_str` config field exists but is not yet used in the auth middleware.

### Flow 2: Express Project Lifecycle (Portal DB path)

```
1. Orchestrator checks portal via ph_list_projects MCP tool
2. If no local manifest found, presents portal projects to user
3. User selects express mode during intake
4. Skill calls ph_create_express_project(name, intake_data) via MCP
5. Portal creates express project record:
   - ExpressProject row with phase=intake, status=in_progress
   - IntakeData stored as JSONB
6. Skill calls ph_rcars_query for base-finding (express-specific)
7. User selects base CI, orders it (manual gate)
8. Skill calls ph_update_express_status(project_id, "environment", "waiting")
9. User confirms environment ready
10. Express skill customizes (separate spec, deferred)
11. Skill calls ph_store_express_artifact(project_id, "recap", content)
12. Portal stores recap, sets status=complete
```

**Key distinction from existing projects:** Express projects have no git repo and no manifest file. State lives entirely in the portal DB. The existing `Project` model assumes `repo_url` is non-null and unique. Express needs a new model or a refactored model that allows null `repo_url`.

### Flow 3: Chatbot Proxy (Hosted access path)

```
1. Portal user opens chatbot widget
2. Frontend opens WebSocket to /api/v1/chat
3. Backend identifies user from OAuth proxy headers (X-Forwarded-Email)
4. User sends natural language message
5. Backend constructs LLM request:
   a. System prompt with PH context + available MCP tools
   b. User message
   c. Tool definitions derived from registered MCP tools
6. Backend streams LLM response via Anthropic API (Claude)
7. If LLM requests tool use:
   a. Backend executes MCP tool locally (same process, no network hop)
   b. Returns tool result to LLM
   c. LLM generates next response chunk
8. Backend streams response tokens back to frontend via WebSocket
9. Frontend renders response in chat widget
```

**Architecture choice: WebSocket over SSE.** The chatbot needs bidirectional communication -- user can send follow-up messages while the LLM is still responding. SSE is strictly server-to-client. WebSocket provides the control needed for conversation flow, mid-stream cancellation, and tool-use interludes where the LLM pauses to execute tools.

**The chatbot reuses the same MCP tool functions, not the MCP network protocol.** The chatbot backend lives in the same process as the MCP server. It calls the Python functions directly -- `ph_rcars_query(...)`, `ph_list_projects()`, etc. -- rather than going through HTTP MCP transport. This avoids unnecessary network round-trips and auth overhead for internal calls.

### Flow 4: Jira Integration (Sync target)

```
1. User or skill requests Jira ticket creation
2. Skill calls ph_jira_create_issue(project_id, summary, description) via MCP
3. PH backend creates Jira issue via REST API:
   a. Read Jira credentials from K8s Secret (PAT or OAuth app token)
   b. POST to https://jira.example.com/rest/api/2/issue
   c. Body: {project, issuetype, summary, description, labels}
4. PH stores Jira issue key in portal DB (linked to PH project)
5. PH updates manifest with Jira reference (if git-based project)
6. Optional webhook: Jira --> PH portal for status sync
```

**Manifest stays source of truth.** Jira is a downstream sync target. Project state, phase transitions, and decisions live in the manifest (or portal DB for express). Jira reflects this state; it does not drive it. This prevents the "two sources of truth" problem.

---

## Patterns to Follow

### Pattern 1: Service Client Abstraction

Every external service gets a client class in `app/services/` with retry logic, timeout handling, and structured error responses. MCP tools delegate to these clients -- they never make HTTP calls directly.

```python
# app/services/rcars_client.py
class RCARSClient:
    def __init__(self, base_url: str, sa_token_path: str):
        self.base_url = base_url
        self._sa_token_path = sa_token_path

    def _get_token(self) -> str:
        """Read SA token fresh each time -- K8s rotates it."""
        with open(self._sa_token_path) as f:
            return f.read().strip()

    async def submit_query(self, query: str, stages: list[str]) -> str:
        """Submit advisor query, return job_id."""
        ...

    async def poll_result(self, job_id: str, timeout: int = 120) -> dict:
        """Poll until complete or timeout. Return result dict."""
        ...

    async def query_and_wait(self, query: str, stages: list[str]) -> dict:
        """Submit + poll. This is what MCP tools call."""
        job_id = await self.submit_query(query, stages)
        return await self.poll_result(job_id, timeout=120)
```

**Why this pattern:** Isolates network, auth, and retry concerns from business logic. If RCARS changes its API, only the client changes. MCP tools and chatbot both use the same client.

### Pattern 2: API Key Auth as FastAPI Middleware

The design spec calls for API key auth on the `/mcp` route only. Internal REST API endpoints remain cluster-internal (no external route). Implement as FastAPI middleware wrapping the MCP ASGI mount, not as FastMCP middleware.

**Why FastAPI middleware, not FastMCP middleware:** The auth decision happens at the HTTP transport level before MCP protocol parsing begins. FastMCP's `Middleware` class operates at the MCP message level (tool calls, resource reads). Transport-level auth should reject unauthorized requests before they reach the MCP layer. FastMCP 3.x supports `auth=JWTVerifier(...)` on the server itself, but for simple API key validation (hash comparison against a Secret), a thin ASGI middleware or FastAPI dependency on the mount path is simpler and avoids coupling to FastMCP's auth abstractions.

```python
# app/mcp/auth.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import hashlib

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, hashed_keys: dict[str, str]):
        super().__init__(app)
        self.hashed_keys = hashed_keys  # {key_name: sha256_hash}

    async def dispatch(self, request, call_next):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"error": "Missing API key"}, 401)
        raw_key = auth[7:]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        if key_hash not in self.hashed_keys.values():
            return JSONResponse({"error": "Invalid API key"}, 401)
        return await call_next(request)
```

### Pattern 3: Express Project as Separate Model

Express projects are structurally different from git-based projects. Rather than overloading the existing `Project` model with nullable fields and conditional logic, use a dedicated `ExpressProject` model.

```python
# app/models/express_project.py
class ExpressProject(Base):
    __tablename__ = "express_projects"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    owner_email = Column(String(255), nullable=False)
    base_ci = Column(String(255), nullable=True)
    phase = Column(String(50), default="intake")  # intake/environment/customize/complete
    status = Column(String(50), default="in_progress")
    intake_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=utcnow)
    artifacts = relationship("ExpressArtifact", back_populates="project")
```

**Why separate model:** Express projects have no `repo_url`, no `manifest`, no `phases` array (they have a fixed 4-phase lifecycle). Mixing them into the existing `Project` model would require nullable FK constraints, conditional joins, and polymorphic query logic. A separate table with a combined view or union query for the portal UI is cleaner.

### Pattern 4: Chatbot as LLM Proxy with Tool-Use Loop

The chatbot is not a separate AI service. It is a thin proxy layer that:
1. Accepts user messages via WebSocket
2. Constructs Anthropic API requests with tool definitions
3. Executes tool calls internally (same Python process)
4. Streams response tokens back

```python
# app/api/chat.py (simplified)
@router.websocket("/chat")
async def chat_endpoint(ws: WebSocket):
    await ws.accept()
    user_email = get_user_from_headers(ws.headers)  # OAuth proxy
    conversation = []

    while True:
        user_msg = await ws.receive_text()
        conversation.append({"role": "user", "content": user_msg})

        # Tool-use loop
        while True:
            stream = client.messages.stream(
                model="claude-sonnet-4-6",
                system=PH_SYSTEM_PROMPT,
                messages=conversation,
                tools=MCP_TOOL_DEFINITIONS,
            )
            async for event in stream:
                if event.type == "content_block_delta":
                    await ws.send_json({"type": "token", "text": event.delta.text})
                elif event.type == "tool_use":
                    result = await execute_tool(event.name, event.input)
                    conversation.append({"role": "assistant", "content": [event]})
                    conversation.append({"role": "user", "content": [{"type": "tool_result", ...}]})
                    continue  # re-enter loop for next LLM response

            break  # no more tool calls, response complete
```

**Key decisions:**
- **No LangChain, no agent framework.** The tool-use loop is ~50 lines of code. Adding a framework would add complexity without value for this use case.
- **Same tools, different transport.** CC users access tools via MCP protocol. Chatbot users access the same tool functions via the LLM proxy. The tools themselves are transport-agnostic.
- **Conversation state in memory per WebSocket.** No need for Redis or DB persistence for active conversations. If the WebSocket disconnects, the conversation is lost. This is acceptable for a chatbot that is a complement to the primary CC interface, not a replacement.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate MCP Gateway Service
**What:** Creating a standalone MCP gateway service separate from the portal backend.
**Why bad:** Duplicates database access, adds a network hop, requires its own deployment pipeline, and creates a synchronization problem between the gateway and the portal for shared state (projects, express data, validation results).
**Instead:** The portal backend IS the MCP gateway. The FastMCP server is mounted at `/mcp` on the existing FastAPI app. One codebase, one deployment, one database connection.

### Anti-Pattern 2: Jira as Source of Truth
**What:** Using Jira issue status to drive PH project lifecycle decisions.
**Why bad:** Creates a bidirectional sync dependency. Jira's data model (issue types, workflows, custom fields) doesn't map cleanly to PH phases. Changes in Jira would need to be validated against PH business rules. Two sources of truth always diverge.
**Instead:** Manifest (git) or portal DB (express) is the source of truth. Jira is a one-way sync target. PH pushes state to Jira; Jira never pushes back (webhooks for display updates only, never for state changes).

### Anti-Pattern 3: OAuth for MCP Access
**What:** Implementing full OAuth 2.0 flow for CC users to access the MCP server.
**Why bad:** Overkill for an internal team tool with < 10 users. OAuth requires a token exchange flow, refresh token management, OIDC provider configuration, and client-side OAuth library integration. All this for users who already have access to the cluster.
**Instead:** API keys stored in a K8s Secret. Generate, hash, distribute. Revoke by removing from the Secret. Simple, sufficient, and aligned with the team's infrastructure (Ansible manages secrets).

### Anti-Pattern 4: Chatbot with its own Tool Registry
**What:** Building a separate tool registry or plugin system for the chatbot.
**Why bad:** Creates tool definition drift between MCP and chatbot. Every new MCP tool would need to be separately registered in the chatbot's system.
**Instead:** Derive chatbot tool definitions from the registered FastMCP tools programmatically. When a new MCP tool is added (e.g., `ph_jira_create_issue`), the chatbot automatically has access to it.

### Anti-Pattern 5: Express State in a Separate Database
**What:** Using a different database or storage system for express project state.
**Why bad:** The portal backend already has PostgreSQL with Alembic migrations. Express projects need to appear alongside regular projects in the portal UI. Separate storage means separate queries, separate backup/restore, and potential consistency issues.
**Instead:** Same PostgreSQL database, new tables via Alembic migration. Express projects are queryable alongside regular projects with a UNION query or separate API endpoints.

---

## Deployment Topology Changes

### New K8s Resources

| Resource | Namespace | Purpose |
|----------|-----------|---------|
| Route `ph-mcp` | publishing-house-dev | External route for `/mcp` path only, TLS edge termination |
| Secret `ph-mcp-api-keys` | publishing-house-dev | SHA-256 hashed API keys for MCP auth |
| Secret `ph-jira-credentials` | publishing-house-dev | Jira PAT or OAuth app credentials |
| ConfigMap `ph-backend-config` | publishing-house-dev | RCARS base URL, Jira base URL, feature flags |

### Modified K8s Resources

| Resource | Change |
|----------|--------|
| Deployment `ph-dashboard-backend` | Add env vars for RCARS URL, Jira URL, MCP API keys Secret mount, feature flags |
| ServiceAccount (backend pod) | Existing SA -- its name goes into RCARS SA allowlist |
| RCARS Deployment (rcars-dev) | Add PH SA to `RCARS_SA_ALLOWLIST_STR` env var |

### Network Paths

| Path | Protocol | Auth | Notes |
|------|----------|------|-------|
| CC --> PH MCP | HTTPS (external Route) | Bearer API key | Only `/mcp` exposed externally |
| Portal UI --> PH API | HTTPS (internal, via OAuth proxy) | OAuth proxy session | Existing pattern, no change |
| PH --> RCARS | HTTP (cross-namespace K8s DNS) | SA token | `http://rcars-api.rcars-dev.svc.cluster.local:8080` |
| PH --> Jira | HTTPS (external SaaS) | Jira PAT or OAuth app | Egress from cluster |
| PH --> Anthropic API | HTTPS (external) | Vertex AI ADC or API key | For chatbot LLM calls |
| Chatbot WS --> PH | WSS (internal, via OAuth proxy) | OAuth proxy session | WebSocket upgrade through OAuth proxy |

### Containerfile Changes

The backend Containerfile needs `oc` CLI baked in for express mode (agent needs to run `oc` commands against user-provided clusters). This is a Containerfile.backend change -- add `oc` binary to the image.

---

## Suggested Build Order (Dependencies)

The components form a dependency chain. Build in this order:

### Layer 1: MCP Gateway Infrastructure (blocks everything else)

**Components:**
- API key auth middleware on `/mcp` route
- External Route for MCP endpoint
- K8s Secret for API keys
- Ansible deployer updates for new resources

**Why first:** Every subsequent feature needs the MCP gateway. CC users need it for RCARS tools. Express mode needs it for project state tools. Chatbot reuses the MCP tool functions. Without the gateway, no external MCP access works.

**Verification:** CC user can connect to `ph-mcp.apps.<cluster>/mcp` with a Bearer API key, list tools, and call `ph_list_projects`.

### Layer 2: RCARS Integration

**Components:**
- RCARS HTTP client (`app/services/rcars_client.py`)
- SA token auth implementation in RCARS middleware (RCARS repo change)
- MCP tools: `ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item`
- RCARS SA allowlist update (RCARS Ansible change)
- NetworkPolicy verification (both namespaces)

**Why second:** RCARS tools are the first real payoff from the MCP gateway. Intake vetting has been broken since the RCARS v2 migration. This fixes it. Express mode also needs RCARS for base-finding queries.

**Dependency:** Requires Layer 1 (MCP gateway must be deployed for CC users to call RCARS tools).

**Cross-repo work:**
- `rhdp-publishing-house-portal`: RCARS client + MCP tools
- `rcars-advisory`: SA token auth middleware + SA allowlist config
- `rhdp-publishing-house-skills`: Intake skill update (replace `curl` with MCP tool reference)

### Layer 3: Express Mode Framework

**Components:**
- Express project DB model + Alembic migration
- Express artifact model
- MCP tools: `ph_create_express_project`, `ph_update_express_status`, `ph_store_express_artifact`, `ph_get_express_project`
- Session continuity tools: `ph_store_intake_results`, `ph_get_intake_results`
- Orchestrator MCP awareness (check local manifest --> check portal --> new intake)
- Portal UI: express project views (kanban, detail, artifact viewer)
- Intake mode selection update (three modes)

**Why third:** Express mode needs both the MCP gateway (Layer 1) and RCARS tools (Layer 2). The express intake flow does RCARS vetting and base-finding before proceeding to the environment gate.

**Dependency:** Requires Layer 1 + Layer 2.

**Note:** The express SKILL (cluster customization agent) is a separate brainstorm+spec, deferred. This layer builds the framework -- intake routing, DB state, portal views. The actual customization agent comes later.

### Layer 4a: Jira Integration (independent of 4b)

**Components:**
- Jira REST client (`app/services/jira_client.py`)
- Jira credentials Secret (Ansible)
- MCP tools: `ph_jira_create_issue`, `ph_jira_link_project`, `ph_jira_get_issue`
- Manifest field for Jira issue reference
- Portal UI: Jira ticket links on project detail

**Why here:** Jira integration needs the MCP gateway (Layer 1) but not RCARS or express. However, it benefits from the patterns established in Layers 1-3 (service client abstraction, MCP tool registration, Ansible secret management). Starting with a brainstorm+spec phase.

**Dependency:** Requires Layer 1. Independent of Layers 2-3.

### Layer 4b: Chatbot Proxy (independent of 4a)

**Components:**
- Chatbot WebSocket endpoint (`app/api/chat.py`)
- LLM proxy service (Anthropic API client)
- Tool-use loop (execute MCP tool functions internally)
- System prompt with PH context
- Frontend chatbot widget (React component)
- `oc` CLI in backend container image (for express mode via chatbot)

**Why here:** The chatbot reuses all MCP tools from Layers 1-3. It provides the same capabilities as CC but through a web UI. Building it last means all the tools it needs already exist.

**Dependency:** Requires Layer 1. Benefits from Layers 2-3 (more tools available). Independent of Layer 4a.

**Note:** Like Jira, this starts with brainstorm+spec before building.

---

## Scalability Considerations

| Concern | At 5 users (now) | At 50 users | At 200+ users |
|---------|-------------------|-------------|---------------|
| MCP connections | Single pod, no issue | Single pod still fine (FastMCP handles sessions in-memory) | Consider connection pooling or horizontal scaling |
| RCARS query load | 1-2 queries/day | 10-20 queries/day, RCARS worker handles via arq queue | RCARS may need worker scaling, not a PH concern |
| Chatbot connections | N/A | 5-10 concurrent WebSockets, single pod handles it | Connection manager + Redis pub/sub for multi-pod |
| Express project DB | < 10 records | < 100 records, trivial | Still trivial for PostgreSQL |
| API key management | 2-3 keys in Secret | 10-20 keys, manual management is fine | Consider API key management UI or self-service |

**Current scale does not require:** Redis for session state, horizontal pod scaling, message queues, or connection pooling beyond what asyncpg provides. Build simple, add complexity when load demands it.

---

## Sources

- [FastMCP HTTP Deployment docs](https://gofastmcp.com/deployment/http) -- HIGH confidence
- [FastMCP Server Middleware docs](https://github.com/prefecthq/fastmcp/blob/main/docs/servers/middleware.mdx) -- HIGH confidence (Context7 verified)
- [FastMCP JWT Verifier and Auth patterns](https://github.com/prefecthq/fastmcp/blob/main/docs/servers/auth/token-verification.mdx) -- HIGH confidence (Context7 verified)
- [Kubernetes ServiceAccount token auth](https://kubernetes.io/docs/concepts/security/service-accounts/) -- HIGH confidence
- [K8s TokenReview API for SA validation](https://kubernetes.io/docs/reference/access-authn-authz/authentication/) -- HIGH confidence
- [Jira REST API](https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/) -- HIGH confidence
- [atlassian-python-api](https://github.com/atlassian-api/atlassian-python-api) -- HIGH confidence
- [Enterprise chatbot architecture (FastAPI + WebSocket)](https://www.charlessieg.com/articles/enterprise-chatbot-react-fastapi-websocket-architecture.html) -- MEDIUM confidence
- [MCP Gateway patterns](https://chatforest.com/guides/mcp-gateway-proxy-patterns/) -- MEDIUM confidence
- Existing codebase analysis (PH portal, RCARS advisory, skills) -- HIGH confidence
