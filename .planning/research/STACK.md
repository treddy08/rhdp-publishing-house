# Technology Stack

**Project:** RHDP Publishing House - Milestone 2 (MCP Gateway, Express, Jira, Chatbot)
**Researched:** 2026-04-30 (updated with version-verified data)
**Scope:** New libraries and patterns needed for RCARS API integration, MCP gateway auth, Jira integration, and portal chatbot. Does NOT re-research the existing stack (FastAPI, SQLAlchemy, Next.js 16, PatternFly 6, etc.).

---

## Recommended Stack Additions

### MCP Server Authentication

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| fastmcp | >=3.2.0 (current: 3.2.4) | MCP server framework (upgrade from `>=2.0` in requirements.txt) | PH already uses fastmcp but pinned at `>=2.0`. Version 3.x adds `Middleware` class with `on_call_tool` hooks and `get_http_headers()` dependency injection -- this is the official mechanism for API key auth on MCP endpoints. The existing `mcp.streamable_http_app()` mount pattern in `main.py` continues to work. v3.2.4 released April 14, 2026. | HIGH |

**Implementation pattern:** FastMCP 3.x `Middleware` subclass extracts `Authorization: Bearer <key>` from HTTP headers via `get_http_headers()`, hashes the raw key with SHA-256 (Python stdlib `hashlib`), and compares against hashed values loaded from the `ph-mcp-api-keys` K8s Secret. This replaces the Keycloak JWT verifier scaffolding currently in `app/mcp/auth.py` (which was never activated -- `MCP_AUTH_ENABLED` defaults to `false`).

Two implementation approaches exist and are documented:

1. **FastMCP Middleware (recommended):** Subclass `Middleware` from `fastmcp.server.middleware`, override `on_call_tool`, use `get_http_headers()` from `fastmcp.server.dependencies`. Rejects at the MCP tool-call level. Official pattern documented in FastMCP middleware docs with an `ApiKeyAuth` example that is nearly identical to what PH needs.

2. **ASGI/Starlette middleware:** Wrap the mounted ASGI app with `BaseHTTPMiddleware` that checks the `Authorization` header before requests reach FastMCP. Rejects at the HTTP transport level. Simpler but less granular (can't protect individual tools).

Use approach 1 (FastMCP Middleware). It integrates with the FastMCP lifecycle, can selectively protect tools, and is the documented best practice. The previous research recommended ASGI middleware, but FastMCP 3.x middleware is cleaner and officially supported.

```python
# Example from FastMCP 3.2.4 official docs (Context7 verified)
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError

class ApiKeyAuth(Middleware):
    def __init__(self, valid_keys: set[str], protected_tools: set[str]):
        self.valid_keys = valid_keys
        self.protected_tools = protected_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        if tool_name not in self.protected_tools:
            return await call_next(context)
        headers = get_http_headers() or {}
        api_key = headers.get("authorization", "").removeprefix("Bearer ")
        # Hash and compare against stored hashes
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash not in self.valid_keys:
            raise ToolError("Invalid API key")
        return await call_next(context)
```

**Source:** [FastMCP Middleware docs](https://gofastmcp.com/servers/middleware) via Context7 `/prefecthq/fastmcp` v3.2.4

### RCARS HTTP Client (Backend-to-Backend)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| httpx | >=0.28.0 (current: 0.28.1) | Async HTTP client for RCARS API calls | Already in requirements.txt at `>=0.27.0`. httpx provides native async support via `AsyncClient` for cross-namespace calls to RCARS (`rcars-api.rcars-dev.svc.cluster.local:8080`). Bump the pin to `>=0.28.0` for latest stable (released Dec 2024, stable). | HIGH |

**Auth pattern:** Read the auto-mounted SA token from `/var/run/secrets/kubernetes.io/serviceaccount/token` on each request (K8s rotates the token; never cache it). Send as `Authorization: Bearer <sa-token>` in httpx requests to RCARS. This matches RCARS v2's existing auth middleware at `src/api/rcars/api/middleware/auth.py`, which checks `X-Forwarded-Email`/`X-Forwarded-User` headers for browser users and will validate SA tokens via TokenReview.

**Note:** RCARS v2 auth middleware currently only handles OAuth proxy headers (`X-Forwarded-Email`). SA token validation (TokenReview) is specified in the RCARS integration design but needs to be implemented in the RCARS repo. The `RCARS_SA_ALLOWLIST_STR` config exists but is not yet wired into the middleware.

### Jira Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| atlassian-python-api | >=4.0.7 | Jira REST API client | Covers the full Atlassian ecosystem (Jira, Confluence, Bitbucket). PH needs Jira issue creation, status updates, and JQL queries. Wraps Jira REST v2/v3 with a clean Python dict/JSON interface. Uses `requests` under the hood (synchronous), but Jira calls are infrequent (project lifecycle events, not per-request) so async is unnecessary. Latest release: v4.0.7, August 21 2025. | MEDIUM |

**Auth for Jira Cloud:** API tokens with basic auth (`email:api_token`). Store the API token in a K8s Secret managed by Ansible. The library constructor accepts `username` (email) and `password` (API token) with `cloud=True`:

```python
from atlassian import Jira

jira = Jira(
    url="https://issues.redhat.com",
    username="user@redhat.com",
    password="<api-token-from-secret>",
    cloud=True,
)
```

**Cloud pagination note:** The traditional `jql()` method is deprecated for Jira Cloud. Atlassian moved to `nextPageToken`-based pagination. Use `enhanced_jql()` instead for Cloud instances.

**Why not `jira` (pycontribs/jira):** Object-oriented abstraction adds layers PH does not need. PH wraps Jira behind MCP tools (`ph_jira_create_issue`, `ph_jira_link_project`), so the thin dict/JSON responses from `atlassian-python-api` map directly to MCP tool return values without conversion. Also covers potential future Confluence integration.

**Why not raw httpx:** Jira REST API is large (200+ endpoints). The library handles pagination, auth header construction, error mapping, and field ID resolution. Rolling our own would be overhead for no benefit.

**Why not the Atlassian Remote MCP Server:** Atlassian provides an official MCP server for Jira/Confluence. However, PH needs Jira as a sync target for PH project lifecycle events (one-directional push), not as an interactive tool for end users. The Atlassian MCP server is designed for users querying/editing Jira via LLM -- PH's integration is programmatic backend-to-backend sync. Wrapping `atlassian-python-api` behind PH MCP tools gives full control over what gets synced and how.

**Source:** [atlassian-python-api PyPI](https://pypi.org/project/atlassian-python-api/), [ReadTheDocs](https://atlassian-python-api.readthedocs.io/)

### Portal Chatbot Backend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| anthropic[vertex] | >=0.97.0 | Anthropic SDK with Vertex AI support | PH uses Vertex AI for Claude access (`ANTHROPIC_VERTEX_PROJECT_ID=itpc-gcp-product-all-claude`). The SDK provides `AnthropicVertex` client with `messages.create()` and `messages.stream()`. Supports tool calling, conversation history management, and SSE streaming. v0.97.0 released April 23, 2026. | HIGH |

**Architecture decision: Direct SDK, not a framework.**

The chatbot backend is a new FastAPI router (`/api/v1/chat`) that:
1. Receives user messages from the portal frontend via POST
2. Maintains conversation history in the portal DB (the Anthropic API is stateless -- PH owns history)
3. Calls Claude via `AnthropicVertex` with tool definitions derived from registered MCP tools
4. Streams text responses back to the frontend via SSE
5. When Claude requests a tool call, the backend executes the corresponding MCP tool function locally (same Python process, no network hop) and returns the result to the LLM for the next response

**Tool dispatch pattern:** The chatbot does NOT call tools through the MCP HTTP protocol. It calls the same Python functions (`ph_rcars_query(...)`, `ph_list_projects()`, etc.) directly. This avoids network round-trips, API key auth overhead, and latency for internal calls. The tool definitions passed to the Anthropic API are derived programmatically from the FastMCP tool registry.

**Why not LiteLLM:** Adds a gateway proxy layer PH does not need. PH uses exactly one LLM provider (Vertex AI Claude). LiteLLM's value is multi-provider abstraction -- pure overhead for a single-provider setup. NOTE: LiteLLM PyPI versions 1.82.7 and 1.82.8 were compromised with credential-stealing malware. Supply chain risk is real.

**Why not LangChain:** PH needs a thin conversation loop, not an agent framework. The chatbot proxies Claude with tool calling -- the Anthropic SDK handles this directly. LangChain adds 50+ transitive dependencies for functionality PH will not use. The tool-use loop is ~50 lines of code.

**Known issue -- Streaming + Tool Calling on Vertex AI:** There is an open bug ([anthropic-sdk-python #1020](https://github.com/anthropics/anthropic-sdk-python/issues/1020)) where `messages.stream()` returns the wrong stream class for Vertex AI beta messages, causing tool input parameters to be lost during streaming. **Workaround:** Use `stream=False` for requests that include tools, `stream=True` for text-only responses. This affects chatbot UX (no token-by-token streaming during tool execution) but is functional. A community fix exists as a fork but has not been merged upstream. Monitor the issue.

**Conversation state:** The Anthropic API is stateless. PH must maintain and resend full conversation history with each request. Store conversation messages in the portal DB, keyed by session ID and user email. Load the full history on each request. For long conversations, use Anthropic's context management features (`clear_tool_uses` edit type) to prune old tool call/result pairs and manage token usage.

**Source:** [Anthropic Python SDK PyPI](https://pypi.org/project/anthropic/), [GitHub](https://github.com/anthropics/anthropic-sdk-python), [Vertex AI docs](https://platform.claude.com/docs/en/build-with-claude/claude-on-vertex-ai)

### Portal Chatbot Frontend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| @patternfly/chatbot | >=6.4.1 | Chat UI components for the portal chatbot | PH already uses PatternFly 6. This is the official PatternFly ChatBot extension, purpose-built for AI chat interfaces. Supports React 19 (PH uses 19.2.4), markdown rendering via react-markdown, code blocks via PatternFly CodeBlock, message actions (copy, feedback), loading states, deep thinking visualization, and tool call display. v6.4.1 is the latest. | HIGH |

**Key components that map to PH chatbot needs:**

| Component | PH Use |
|-----------|--------|
| `<Message>` with markdown content | Claude responses render with proper formatting |
| `isLoading` state | Shows during Claude API calls and tool execution |
| Source display (RAG sources) | Can display RCARS results inline in chat messages |
| Tool call visualization | Shows when chatbot calls `ph_rcars_query`, etc. |
| Deep thinking display | Shows Claude's reasoning (extended thinking) |
| Message actions (copy, feedback) | Users can copy responses, rate quality |
| Chat history drawer | Browse previous conversations |
| MessageBar (input) | User message input with send button |

**Why not shadcn/ui, assistant-ui, or custom:** PH is a PatternFly application. Mixing design systems creates visual inconsistency and doubles CSS maintenance. The PatternFly ChatBot extension matches the existing design language, follows Red Hat's accessibility standards, and is actively maintained by the PatternFly team with Q2 2025 React 19 support.

**CSS import note:** The `@patternfly/chatbot` CSS must be imported last in the entry file to properly override PatternFly component styles.

```bash
npm install @patternfly/chatbot@^6.4.1
```

**Source:** [@patternfly/chatbot npm](https://www.npmjs.com/package/@patternfly/chatbot), [PatternFly ChatBot docs](https://www.patternfly.org/patternfly-ai/chatbot/about-chatbot/), [PatternFly Release Highlights Q2 2025](https://www.patternfly.org/get-started/release-highlights/)

### SSE Streaming (Backend to Frontend)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| sse-starlette | >=2.0.0 | Server-Sent Events for FastAPI | Provides `EventSourceResponse` for streaming Claude responses from the chatbot backend to the React frontend. FastAPI does not include SSE natively. RCARS uses the same pattern for its advisor progress streaming (Redis pub/sub -> SSE). | MEDIUM |

**Why SSE instead of WebSockets (correcting previous research):**

The previous research recommended WebSockets for bidirectional communication. After deeper analysis, SSE is the better choice:

1. **User input and LLM streaming are separate concerns.** The user sends a message via a standard POST request. The server streams the response via SSE. There is no need for a persistent bidirectional channel.
2. **SSE auto-reconnects.** If the connection drops, the browser's `EventSource` API automatically reconnects. WebSockets require manual reconnection logic.
3. **SSE works through HTTP proxies, load balancers, and CDNs** without special configuration. OpenShift Routes handle SSE natively. WebSocket upgrade requires explicit proxy configuration.
4. **Mid-conversation messages:** If the user wants to send a follow-up while the LLM is responding, they can POST to a cancel endpoint to abort the current stream, then POST a new message. This is the same pattern used by ChatGPT, Claude.ai, and most production chat UIs.
5. **RCARS already uses SSE.** The pattern is proven in the same infrastructure.

**Pattern:**
```
POST /api/v1/chat/message → starts LLM call, returns SSE stream
POST /api/v1/chat/cancel → aborts current stream
GET  /api/v1/chat/history → loads conversation history
```

**Source:** RCARS uses `streaming.py` with Redis pub/sub -> SSE relay. Pattern is proven on the same OpenShift cluster.

---

## Full Stack Summary

### Existing (No Changes Needed)

| Technology | Version | Layer |
|------------|---------|-------|
| FastAPI | >=0.115.0 | Backend framework |
| SQLAlchemy | >=2.0 | ORM |
| Alembic | >=1.13 | Database migrations |
| PostgreSQL | 16 | Database |
| psycopg2-binary | >=2.9 | DB driver |
| Pydantic | >=2.0 | Schemas |
| pydantic-settings | >=2.0 | Configuration |
| APScheduler | >=3.10 | Background jobs |
| PyYAML | >=6.0 | YAML parsing |
| Uvicorn | >=0.30.0 | ASGI server |
| Next.js | 16.2.3 | Frontend framework |
| React | 19.2.4 | UI library |
| @patternfly/react-core | ^6.4.1 | Design system |
| @patternfly/react-table | ^6.4.1 | Table components |
| @patternfly/react-icons | ^6.4.0 | Icons |
| TypeScript | ^5 | Frontend language |

### New (This Milestone)

| Technology | Version | Layer | Phase | Confidence |
|------------|---------|-------|-------|------------|
| fastmcp | >=3.2.0 | MCP server (upgrade) | RCARS integration | HIGH |
| httpx | >=0.28.0 | RCARS HTTP client (bump) | RCARS integration | HIGH |
| atlassian-python-api | >=4.0.7 | Jira REST API | Jira integration | MEDIUM |
| anthropic[vertex] | >=0.97.0 | Claude/Vertex AI SDK | Portal chatbot | HIGH |
| @patternfly/chatbot | >=6.4.1 | Chat UI components | Portal chatbot | HIGH |
| sse-starlette | >=2.0.0 | SSE streaming | Portal chatbot | MEDIUM |

### Removed (This Milestone)

| Technology | Reason |
|------------|--------|
| Keycloak JWT auth scaffolding (`app/mcp/auth.py` KeycloakTokenVerifier) | Replaced by API key auth via FastMCP Middleware. The KeycloakTokenVerifier was never activated (`MCP_AUTH_ENABLED` defaults to `false`). API key auth is the spec'd approach -- simpler, sufficient for internal team. Remove the Keycloak settings from config.py. |
| pyjwt[crypto] (planned, never added to requirements.txt) | No longer needed without Keycloak. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| MCP auth | FastMCP Middleware + SHA-256 API keys | Keycloak JWT, OAuth 2.1, ASGI middleware | OAuth overkill for <20 internal users. ASGI middleware works but FastMCP Middleware is the officially documented pattern with tool-level granularity. Keycloak adds infrastructure dependency PH does not need. |
| MCP auth implementation | FastMCP `Middleware.on_call_tool` | Starlette `BaseHTTPMiddleware` | FastMCP Middleware operates at the MCP protocol level with tool-level granularity. `BaseHTTPMiddleware` operates at HTTP level -- coarser, can't selectively protect individual tools. |
| HTTP client | httpx (async) | requests, aiohttp | httpx already in deps, async-native, better type hints. aiohttp has a less ergonomic API. requests is synchronous. |
| Jira client | atlassian-python-api | jira (pycontribs), raw httpx, Atlassian MCP server | `jira` adds object abstraction PH does not need. Raw httpx means reimplementing pagination and field resolution. Atlassian MCP server is for interactive LLM-user Jira access, not programmatic backend sync. |
| LLM SDK | anthropic[vertex] | LiteLLM, LangChain, raw HTTP | Single provider (Vertex AI) -- gateway/framework abstraction is overhead. LiteLLM had a supply chain compromise. LangChain adds 50+ deps for a 50-line tool-use loop. |
| Chat UI | @patternfly/chatbot | shadcn/ui, assistant-ui, custom React | PH is a PatternFly app. Design system consistency. Official Red Hat extension with AI-specific components (tool calls, deep thinking, RAG sources). |
| Streaming | SSE (sse-starlette) | WebSockets | Unidirectional stream is sufficient for LLM response delivery. SSE auto-reconnects, works through HTTP proxies natively. POST for user input, SSE for response -- same pattern as ChatGPT/Claude.ai. |
| Chatbot architecture | Direct Anthropic SDK + tool dispatch | LangChain agents, Claude Agent SDK, AutoGen | PH chatbot is thin: receive message, call Claude with tools, stream response. No agent orchestration framework needed. The tool-use loop is 50 lines, not a framework problem. |

---

## Installation

### Backend (Python)

```bash
# Update requirements.txt with these additions/changes:
fastmcp>=3.2.0          # was >=2.0
httpx>=0.28.0           # was >=0.27.0
atlassian-python-api>=4.0.7   # NEW
anthropic[vertex]>=0.97.0     # NEW
sse-starlette>=2.0.0          # NEW

# Install
pip install -r requirements.txt
```

### Frontend (npm)

```bash
cd src/frontend
npm install @patternfly/chatbot@^6.4.1
```

Then add CSS import as the **last** import in the entry file:
```typescript
import '@patternfly/chatbot/dist/css/main.css';
```

---

## Configuration Additions

New settings needed in `app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # MCP API key auth (replaces Keycloak settings)
    mcp_api_keys_file: Optional[str] = None  # Path to mounted keys.yaml Secret volume

    # RCARS integration
    rcars_api_url: str = "http://rcars-api.rcars-dev.svc.cluster.local:8080"
    rcars_request_timeout: int = 120  # seconds, matches design spec
    rcars_poll_interval: int = 3      # seconds between poll attempts

    # Jira integration
    jira_url: Optional[str] = None          # e.g. https://issues.redhat.com
    jira_email: Optional[str] = None        # Service account email
    jira_api_token: Optional[str] = None    # From K8s Secret, gitignored
    jira_default_project: Optional[str] = None  # Default Jira project key

    # Chatbot
    anthropic_vertex_project_id: Optional[str] = None  # e.g. itpc-gcp-product-all-claude
    anthropic_vertex_region: str = "us-east5"
    chatbot_model: str = "claude-sonnet-4-6"   # Cost-effective for interactive chat
    chatbot_max_tokens: int = 4096
    chatbot_enabled: bool = False  # Feature flag, disabled until ready

    # Remove these (Keycloak auth -- never activated)
    # mcp_auth_enabled: bool = False
    # keycloak_realm_url: Optional[str] = None
```

---

## Version Verification Summary

| Package | Pinned | Current (PyPI/npm) | Verified Via | Date Checked |
|---------|--------|--------------------|-------------|--------------|
| fastmcp | >=3.2.0 | 3.2.4 | Context7 + PyPI | 2026-04-30 |
| httpx | >=0.28.0 | 0.28.1 | PyPI | 2026-04-30 |
| atlassian-python-api | >=4.0.7 | 4.0.7 | PyPI + ReadTheDocs | 2026-04-30 |
| anthropic[vertex] | >=0.97.0 | 0.97.0 | PyPI + GitHub releases | 2026-04-30 |
| @patternfly/chatbot | ^6.4.1 | 6.4.1 | npm registry | 2026-04-30 |
| sse-starlette | >=2.0.0 | not pinpointed | PyPI search | 2026-04-30 |

---

## Sources

### HIGH Confidence (Context7 / Official Docs)
- [FastMCP 3.2.4 - Middleware docs](https://gofastmcp.com/servers/middleware) -- Context7 `/prefecthq/fastmcp` v3.2.4, verified `ApiKeyAuth` pattern
- [FastMCP 3.2.4 - HTTP Deployment](https://gofastmcp.com/deployment/http) -- Context7 verified
- [FastMCP 3.2.4 - Dependency Injection](https://gofastmcp.com/servers/dependency-injection) -- Context7 verified `get_http_headers()`, `CurrentRequest()`
- [FastMCP 3.2.4 - Server Auth](https://gofastmcp.com/python-sdk/fastmcp-server-auth-auth) -- Context7 verified `verify_token`, `BearerAuthProvider`
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) -- v3.2.4, April 14 2026
- [Anthropic Python SDK PyPI](https://pypi.org/project/anthropic/) -- v0.97.0, April 23 2026
- [Anthropic Python SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) -- streaming, tool_use, AnthropicVertex
- [Anthropic Vertex AI docs](https://platform.claude.com/docs/en/build-with-claude/claude-on-vertex-ai)
- [PatternFly ChatBot npm](https://www.npmjs.com/package/@patternfly/chatbot) -- v6.4.1
- [PatternFly ChatBot docs](https://www.patternfly.org/patternfly-ai/chatbot/about-chatbot/) -- React 19 support, message components
- [PatternFly Release Highlights](https://www.patternfly.org/get-started/release-highlights/) -- Q2 2025 React 19 confirmation
- [httpx docs](https://www.python-httpx.org/) -- v0.28.1, async support

### MEDIUM Confidence (PyPI / WebSearch verified)
- [atlassian-python-api PyPI](https://pypi.org/project/atlassian-python-api/) -- v4.0.7, August 2025
- [atlassian-python-api ReadTheDocs](https://atlassian-python-api.readthedocs.io/) -- Jira Cloud auth, `enhanced_jql`
- [Jira Cloud API token auth](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/)
- [Anthropic SDK Vertex AI streaming + tools bug](https://github.com/anthropics/anthropic-sdk-python/issues/1020) -- open issue, community fix exists

### Referenced (Patterns / Architecture)
- [FastMCP + FastAPI integration guide](https://gofastmcp.com/integrations/fastapi)
- [FastMCP middleware auth blog](https://gelembjuk.com/blog/post/authentication-remote-mcp-server-python/)
- [FastMCP auth issue #2817](https://github.com/PrefectHQ/fastmcp/issues/2817) -- combined app auth challenges
- [Atlassian Remote MCP Server](https://github.com/atlassian/atlassian-mcp-server) -- evaluated, not recommended for PH use case
