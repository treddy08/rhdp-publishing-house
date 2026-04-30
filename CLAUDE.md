<!-- GSD:project-start source:PROJECT.md -->
## Project

**RHDP Publishing House**

AI-powered content lifecycle management for Red Hat Demo Platform. One command — `/rhdp-publishing-house` — provides a persistent, state-aware orchestrator that manages the entire content lifecycle (intake, writing, editing, automation, review, publishing) through specialized Claude Code agent skills. Content developers become content architects: design the architecture, agents handle the writing, editing, automation, and review.

**Core Value:** Content developers can create production-quality RHDP workshops and demos without juggling multiple tools, skills, or processes — one entry point orchestrates the entire pipeline from idea to published catalog item.

### Constraints

- **Multi-repo:** Changes span `rhdp-publishing-house`, `rhdp-publishing-house-portal`, `rhdp-publishing-house-skills`, and `rcars-advisory`. GSD tracks work centrally but commits happen in each repo.
- **Dependency chain:** RCARS integration must land before express mode (express needs MCP tools). Jira and chatbot brainstorms are independent of each other but benefit from RCARS being in place.
- **RCARS v2 API stability:** RCARS v2 is deployed but the API surface may evolve. PH wraps RCARS behind MCP tools so skill code is insulated from API changes.
- **Auth model:** API key auth for external MCP access, SA token for cluster-internal RCARS calls. No OAuth for this milestone.
- **Ansible deployers:** All infrastructure changes (routes, secrets, config) go through Ansible — no manual `oc edit`.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack Additions
### MCP Server Authentication
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| fastmcp | >=3.2.0 (current: 3.2.4) | MCP server framework (upgrade from `>=2.0` in requirements.txt) | PH already uses fastmcp but pinned at `>=2.0`. Version 3.x adds `Middleware` class with `on_call_tool` hooks and `get_http_headers()` dependency injection -- this is the official mechanism for API key auth on MCP endpoints. The existing `mcp.streamable_http_app()` mount pattern in `main.py` continues to work. v3.2.4 released April 14, 2026. | HIGH |
# Example from FastMCP 3.2.4 official docs (Context7 verified)
### RCARS HTTP Client (Backend-to-Backend)
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| httpx | >=0.28.0 (current: 0.28.1) | Async HTTP client for RCARS API calls | Already in requirements.txt at `>=0.27.0`. httpx provides native async support via `AsyncClient` for cross-namespace calls to RCARS (`rcars-api.rcars-dev.svc.cluster.local:8080`). Bump the pin to `>=0.28.0` for latest stable (released Dec 2024, stable). | HIGH |
### Jira Integration
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| atlassian-python-api | >=4.0.7 | Jira REST API client | Covers the full Atlassian ecosystem (Jira, Confluence, Bitbucket). PH needs Jira issue creation, status updates, and JQL queries. Wraps Jira REST v2/v3 with a clean Python dict/JSON interface. Uses `requests` under the hood (synchronous), but Jira calls are infrequent (project lifecycle events, not per-request) so async is unnecessary. Latest release: v4.0.7, August 21 2025. | MEDIUM |
### Portal Chatbot Backend
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| anthropic[vertex] | >=0.97.0 | Anthropic SDK with Vertex AI support | PH uses Vertex AI for Claude access (`ANTHROPIC_VERTEX_PROJECT_ID=itpc-gcp-product-all-claude`). The SDK provides `AnthropicVertex` client with `messages.create()` and `messages.stream()`. Supports tool calling, conversation history management, and SSE streaming. v0.97.0 released April 23, 2026. | HIGH |
### Portal Chatbot Frontend
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| @patternfly/chatbot | >=6.4.1 | Chat UI components for the portal chatbot | PH already uses PatternFly 6. This is the official PatternFly ChatBot extension, purpose-built for AI chat interfaces. Supports React 19 (PH uses 19.2.4), markdown rendering via react-markdown, code blocks via PatternFly CodeBlock, message actions (copy, feedback), loading states, deep thinking visualization, and tool call display. v6.4.1 is the latest. | HIGH |
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
### SSE Streaming (Backend to Frontend)
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| sse-starlette | >=2.0.0 | Server-Sent Events for FastAPI | Provides `EventSourceResponse` for streaming Claude responses from the chatbot backend to the React frontend. FastAPI does not include SSE natively. RCARS uses the same pattern for its advisor progress streaming (Redis pub/sub -> SSE). | MEDIUM |
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
## Installation
### Backend (Python)
# Update requirements.txt with these additions/changes:
# Install
### Frontend (npm)
## Configuration Additions
## Version Verification Summary
| Package | Pinned | Current (PyPI/npm) | Verified Via | Date Checked |
|---------|--------|--------------------|-------------|--------------|
| fastmcp | >=3.2.0 | 3.2.4 | Context7 + PyPI | 2026-04-30 |
| httpx | >=0.28.0 | 0.28.1 | PyPI | 2026-04-30 |
| atlassian-python-api | >=4.0.7 | 4.0.7 | PyPI + ReadTheDocs | 2026-04-30 |
| anthropic[vertex] | >=0.97.0 | 0.97.0 | PyPI + GitHub releases | 2026-04-30 |
| @patternfly/chatbot | ^6.4.1 | 6.4.1 | npm registry | 2026-04-30 |
| sse-starlette | >=2.0.0 | not pinpointed | PyPI search | 2026-04-30 |
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
