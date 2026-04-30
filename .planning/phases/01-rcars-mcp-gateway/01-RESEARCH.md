# Phase 1: RCARS MCP Gateway - Research

**Researched:** 2026-04-30
**Domain:** MCP gateway with API key auth, RCARS v2 HTTP client, cross-repo deployment
**Confidence:** HIGH

## Summary

Phase 1 wraps RCARS v2 behind authenticated MCP tools in the PH portal backend, replacing the intake skill's broken `curl` call to a nonexistent `/recommend` endpoint. The work spans four repos: portal backend (MCP tools + auth + RCARS client), RCARS advisory (SA allowlist wiring), skills plugin (intake skill fix), and this repo (documentation).

The core technical challenge is a FastMCP 2.0 to 3.2+ migration that enables the `Middleware` class for API key auth via `on_call_tool` hooks. This migration is well-documented and the existing codebase is minimal (one server file, one tools file), making it low-risk. The RCARS HTTP client is straightforward httpx async work against a well-understood API surface (advisor query/poll, catalog browse/detail, health check).

**Critical discovery during research:** RCARS's `sa_allowlist_str` config field exists in Python code but has NO corresponding auth middleware implementation. The current RCARS auth relies entirely on `X-Forwarded-Email` / `X-Forwarded-User` headers from the OAuth proxy. Requirements RCARS-02 (SA token validation via TokenReview) and RCARS-03 (SA allowlist wiring) require building new auth middleware in the RCARS codebase AND wiring the `RCARS_SA_ALLOWLIST_STR` env var through Ansible templates. This is more work than the design spec anticipated.

**Primary recommendation:** Build the RCARS client to initially authenticate via the SA token in the `Authorization: Bearer` header, but implement the RCARS-side TokenReview middleware as a separate, clearly-scoped cross-repo task. The PH side can be fully tested before the RCARS auth middleware is deployed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Pod restart for key changes in Phase 1 -- backend reads API keys from the volume-mounted Secret file at startup only. No hot-reload mechanism. To add or revoke a key: update Ansible vars, redeploy, pod restarts.
- **D-02:** Manual key generation workflow: `openssl rand -hex 32`, SHA-256 hash, paste into Ansible vars file, redeploy. No CLI helper tooling. Document the workflow clearly in the admin guide.
- **D-03:** API keys stored as a volume-mounted K8s Secret file (not env var). Leaves the door open for hot-reload later without changing the storage approach.
- **D-04:** Retry with exponential backoff (3 attempts, 1s/2s/4s delays) in the RCARS HTTP client layer for transient failures (5xx, connection errors). Fail fast on 4xx (auth errors). Skills never see transient failures -- they get the final result or a clean "RCARS unavailable" error.
- **D-05:** Moderate error verbosity -- include enough context for developer diagnosis (retry count, failure type, service name) but no raw stack traces. Example: "RCARS query failed after 3 retries (connection timeout to rcars-api service). Vetting skipped."
- **D-06:** Health endpoint (`/health`) actively probes RCARS on every request (calls RCARS health or lightweight endpoint). Reports accurate real-time connectivity status.
- **D-07:** Dependency order execution: (1) RCARS SA allowlist change in `rcars-advisory` -> (2) Portal backend MCP gateway in `rhdp-publishing-house-portal` -> (3) Intake skill update in `rhdp-publishing-house-skills` -> (4) Documentation in `rhdp-publishing-house`. Each step verifiable before the next.
- **D-08:** Config changes only for RCARS -- prepare the Ansible vars change and document the deploy command. User runs the deployer manually. No automated deployment during plan execution.
- **D-09:** Branch strategy: `gsd-project` branch for all PH repos (portal, skills-plugin, this repo). Direct commits to `main` for `rcars-advisory` (rcars-dev builds from main, rcars-prod builds from production -- we only touch dev).
- **D-10:** Submodule awareness: `skills-plugin` and `template` are git submodules in `rhdp-publishing-house`. Changes committed through the main dev repo. Local clones of these repos must be pulled after commits to stay in sync.
- **D-11:** All 5 documentation deliverables ship alongside code, not after. Documentation is a first-class requirement. If RCARS documentation needs updating to match the integration, those changes are in scope too (committed to `rcars-advisory` main).
- **D-12:** All documentation lives in this repo (`rhdp-publishing-house`) under `docs/`, even for features implemented in the portal repo. Single source of truth for PH docs.

### Claude's Discretion
- FastMCP 2.0 -> 3.2+ migration approach (how to handle breaking changes)
- httpx AsyncClient configuration (connection pooling, timeout values beyond the spec's 120s advisor timeout)
- RCARS HTTP client module structure (single module vs. service class)
- Exact health check probe implementation (which RCARS endpoint to call)
- Keycloak auth scaffolding removal approach (clean delete vs. gradual replacement)

### Deferred Ideas (OUT OF SCOPE)
- Browser-based API key provisioning via Red Hat SSO callback -- future milestone, replaces manual openssl+ansible workflow
- Portal repo consolidation into main dev repo -- user flagged dissatisfaction with separate portal repo
- Hot-reload for API key Secret -- volume-mount storage choice preserves this option for later
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCP-01 | External `/mcp` HTTPS endpoint deployed with API key auth (SHA-256, hmac.compare_digest, Ansible-managed Secret) | FastMCP 3.2+ Middleware `on_call_tool` pattern verified via Context7. Ansible template pattern established in existing infra template. Volume-mount Secret pattern documented. |
| MCP-02 | FastMCP 3.2+ middleware validates API key on every tool call via `on_call_tool` hook | Context7-verified `ApiKeyAuth(Middleware)` pattern with `get_http_headers(include={"authorization"})`. NOTE: default `get_http_headers()` strips auth header. |
| MCP-03 | Invalid/missing API key returns 401; valid key proceeds to tool dispatch | FastMCP `ToolError` for rejection. `hmac.compare_digest` for timing-safe comparison. SHA-256 hashing via `hashlib.sha256`. |
| MCP-04 | `ph_rcars_query(query)` submits advisor query, polls until complete (3s interval, 120s timeout), returns structured results | RCARS API: `POST /api/v1/advisor/query` returns `{job_id}`, poll `GET /api/v1/advisor/query/{job_id}/result` returns `{status, result, error}`. Query model: `QueryRequest(query, event_url, stages, include_zt, opted_out)`. |
| MCP-05 | `ph_rcars_catalog_search(query, limit)` returns paginated RCARS catalog items | RCARS API: `GET /api/v1/catalog?limit={limit}&offset={offset}&stage={stage}&category={category}`. Returns `{items, total}`. |
| MCP-06 | `ph_rcars_catalog_item(ci_name)` returns full metadata for specific catalog item | RCARS API: `GET /api/v1/catalog/{ci_name}`. Returns item + analysis + tags merged dict. |
| MCP-07 | Health check endpoint reports RCARS connectivity status | RCARS has `GET /api/v1/health` (simple ok) and `GET /api/v1/health/ready` (db+redis checks). Use `/api/v1/health` for lightweight probe. |
| MCP-08 | Ansible deployer manages Route, API key Secret, and all K8s resource changes | Existing Ansible deployer uses Jinja2 templates + `kubernetes.core.k8s`. Add Route and Secret to `manifests-infra.yaml.j2`. Add `mcp_api_keys` and `mcp_route_host` vars. |
| RCARS-01 | PH backend SA token re-read from filesystem on every RCARS request (not cached) | K8s auto-mounts SA token at `/var/run/secrets/kubernetes.io/serviceaccount/token`. Read with `open()` on each request. Token rotates automatically. |
| RCARS-02 | RCARS middleware validates SA token via K8s TokenReview API | **NEW WORK REQUIRED**: RCARS `auth.py` currently uses `X-Forwarded-Email` headers only. `sa_allowlist_str` config exists but NO middleware uses it. Must build new SA auth dependency in RCARS. |
| RCARS-03 | PH backend SA added to `RCARS_SA_ALLOWLIST_STR` in RCARS Ansible vars | **NEW WORK REQUIRED**: `RCARS_SA_ALLOWLIST_STR` env var not in RCARS Ansible template (`manifests-app.yaml.j2`). Must add env var to template AND add SA value to vars files. |
| RCARS-04 | Cross-namespace connectivity verified and unblocked | RCARS API Service is `rcars-api.rcars-dev.svc.cluster.local:8080` (ClusterIP). Verify no restrictive NetworkPolicies. Ansible deploy can include smoke test. |
| RCARS-05 | Intake skill replaces broken `curl` with `ph_rcars_query` MCP tool reference | Intake `SKILL.md` lines 216-260: replace `curl` block with MCP tool reference. Change availability check from `integrations.rcars_api` URL to MCP tool availability. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| API key auth (external MCP) | API / Backend (PH portal) | -- | Auth must happen server-side; FastMCP Middleware intercepts before tool dispatch |
| SA token auth (cluster-internal) | API / Backend (RCARS) | API / Backend (PH portal) | RCARS validates tokens; PH reads and sends SA token |
| RCARS data queries | API / Backend (PH portal) | -- | PH backend is single gateway; skills never call RCARS directly |
| Intake vetting logic | Claude Code (skill) | -- | Skills interpret RCARS results against project context; PH backend only provides data |
| K8s Secret management | CDN / Static (Ansible) | -- | Ansible deployer manages all K8s resources; no manual oc commands |
| Health check / monitoring | API / Backend (PH portal) | -- | Portal health endpoint probes RCARS and reports status |
| Documentation | Static (this repo) | -- | All docs in `rhdp-publishing-house/docs/` per D-12 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastmcp | >=3.2.0 (current: 3.2.4) | MCP server framework with Middleware auth | Required for `on_call_tool` hooks and `get_http_headers()` DI. Upgrade from existing `>=2.0` pin. [VERIFIED: PyPI registry, Context7 /prefecthq/fastmcp] |
| httpx | >=0.28.0 (current: 0.28.1) | Async HTTP client for RCARS API calls | Already in requirements.txt at `>=0.27.0`. Native async, connection pooling, timeout config. [VERIFIED: PyPI registry] |
| FastAPI | >=0.115.0 | Backend framework (existing) | Already deployed, no changes needed. [VERIFIED: codebase] |
| Pydantic | >=2.0 | Request/response schemas | Already deployed, used for Settings and models. [VERIFIED: codebase] |
| pydantic-settings | >=2.0 | Configuration management | Already deployed, Settings class. [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib | stdlib | SHA-256 hashing for API keys | API key comparison in auth middleware |
| hmac | stdlib | Timing-safe comparison | `hmac.compare_digest()` prevents timing attacks |
| asyncio | stdlib | Async polling loop | Advisor query poll (3s interval, 120s timeout) |
| pathlib | stdlib | File path handling | Reading SA token and API key Secret files |
| pyyaml | >=6.0 | YAML parsing for API key Secret | Parse `keys.yaml` from volume-mounted Secret |

### Removed (This Phase)
| Library | Reason |
|---------|--------|
| Keycloak JWT scaffolding (`app/mcp/auth.py` KeycloakTokenVerifier) | Replaced by API key auth via FastMCP Middleware. Never activated (`MCP_AUTH_ENABLED` defaults to `false`). [VERIFIED: codebase `server.py` line 28] |
| pyjwt[crypto] (planned, never added) | No longer needed without Keycloak. [VERIFIED: not in requirements.txt] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastMCP Middleware auth | Starlette BaseHTTPMiddleware | Starlette middleware operates at HTTP level -- coarser, can't selectively protect individual tools. FastMCP Middleware works at MCP protocol level with tool-level granularity. [CITED: gofastmcp.com/servers/middleware] |
| `get_http_headers(include={"authorization"})` | `CurrentHeaders()` DI | `CurrentHeaders()` includes all headers but requires DI injection. `get_http_headers()` is callable anywhere but strips auth by default. Use `include={"authorization"}` in middleware. [VERIFIED: Context7] |
| httpx AsyncClient | requests, aiohttp | httpx already in deps, async-native, better timeout/retry API. [VERIFIED: requirements.txt] |

**Installation (requirements.txt changes):**
```
# Change:
fastmcp>=2.0  ->  fastmcp>=3.2.0
httpx>=0.27.0  ->  httpx>=0.28.0
```

No new packages required. All dependencies are already in requirements.txt; only version pins need bumping.

## Architecture Patterns

### System Architecture Diagram

```
                                   ┌──────────────────────────┐
                                   │  Claude Code User        │
                                   │  (with API key in        │
                                   │   MCP config)            │
                                   └────────┬─────────────────┘
                                            │ Authorization: Bearer <raw-key>
                                            │ HTTPS (edge TLS)
                                            ▼
                              ┌─────────────────────────────┐
                              │  OpenShift Route (ph-mcp)   │
                              │  host: ph-mcp.apps.<domain> │
                              │  path: /mcp                 │
                              └────────┬────────────────────┘
                                       │ HTTP (cluster-internal)
                                       ▼
                     ┌─────────────────────────────────────────┐
                     │  PH Portal Backend (FastAPI)            │
                     │  ┌──────────────────────────────────┐   │
                     │  │  FastMCP 3.2+ Server             │   │
                     │  │  mounted at /mcp                 │   │
                     │  │                                  │   │
                     │  │  ┌───────────────────────────┐   │   │
                     │  │  │  ApiKeyAuth Middleware     │   │   │
                     │  │  │  on_call_tool hook         │   │   │
                     │  │  │  SHA-256 hash + compare    │   │   │
                     │  │  │  Keys from volume-mount    │   │   │
                     │  │  └───────────┬───────────────┘   │   │
                     │  │              │ authenticated      │   │
                     │  │              ▼                    │   │
                     │  │  ┌───────────────────────────┐   │   │
                     │  │  │  MCP Tools                │   │   │
                     │  │  │  - ph_rcars_query         │   │   │
                     │  │  │  - ph_rcars_catalog_search│   │   │
                     │  │  │  - ph_rcars_catalog_item  │   │   │
                     │  │  │  - ph_list_projects       │   │   │
                     │  │  │  - ph_get_launch_instr... │   │   │
                     │  │  └───────────┬───────────────┘   │   │
                     │  └──────────────┼───────────────────┘   │
                     │                 │                        │
                     │  ┌──────────────▼───────────────────┐   │
                     │  │  RCARS HTTP Client (httpx)       │   │
                     │  │  - Async with connection pool    │   │
                     │  │  - Retry: 3x exponential backoff │   │
                     │  │  - SA token from filesystem      │   │
                     │  │  - Timeout: 120s (advisor)       │   │
                     │  └──────────────┬───────────────────┘   │
                     │                 │                        │
                     │  /health ───────┼── probes RCARS health │
                     └─────────────────┼───────────────────────┘
                                       │ Authorization: Bearer <sa-token>
                                       │ HTTP (cross-namespace)
                                       ▼
                     ┌─────────────────────────────────────────┐
                     │  RCARS API (rcars-dev namespace)        │
                     │  rcars-api.rcars-dev.svc.cluster.local  │
                     │  :8080                                  │
                     │                                         │
                     │  /api/v1/health                         │
                     │  /api/v1/advisor/query       (POST)     │
                     │  /api/v1/advisor/query/{id}/result (GET)│
                     │  /api/v1/catalog             (GET)      │
                     │  /api/v1/catalog/{ci_name}   (GET)      │
                     │                                         │
                     │  Auth: SA token via new middleware       │
                     │  (or X-Forwarded-Email via OAuth proxy)  │
                     └─────────────────────────────────────────┘
```

### Recommended Project Structure (Portal Backend Changes)

```
src/backend/app/
├── mcp/
│   ├── __init__.py
│   ├── server.py          # FastMCP 3.2+ instance + ApiKeyAuth middleware (MODIFY)
│   ├── auth.py            # REPLACE: Keycloak -> API key auth middleware class
│   ├── tools.py           # Existing DB tools (KEEP)
│   └── rcars_tools.py     # NEW: ph_rcars_query, ph_rcars_catalog_search, ph_rcars_catalog_item
├── core/
│   ├── config.py          # MODIFY: add RCARS and MCP auth settings
│   └── ...
├── services/
│   └── rcars_client.py    # NEW: httpx AsyncClient wrapper with retry + SA token
├── api/
│   └── health.py          # MODIFY: add RCARS connectivity probe
└── main.py                # MODIFY: update MCP mount for FastMCP 3.2+ lifespan
```

### Pattern 1: FastMCP 3.2+ Middleware for API Key Auth
**What:** Subclass `Middleware` to intercept all tool calls, extract and validate API key from `Authorization: Bearer` header before dispatch.
**When to use:** Every MCP tool call from external clients.
**Example:**
```python
# Source: Context7 /prefecthq/fastmcp — middleware.mdx + dependency-injection.mdx
import hashlib
import hmac
from pathlib import Path
from typing import Optional

import yaml
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError


class ApiKeyAuth(Middleware):
    """Validate API key on every tool call via SHA-256 hash comparison."""

    def __init__(self, keys_file: Path):
        self._keys_file = keys_file
        self._valid_hashes: dict[str, str] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Read YAML map of key-name -> sha256-hash from volume-mounted Secret."""
        if self._keys_file.exists():
            with open(self._keys_file) as f:
                data = yaml.safe_load(f) or {}
            self._valid_hashes = {
                name: h.removeprefix("sha256:") for name, h in data.items()
            }

    def _verify_key(self, raw_key: str) -> bool:
        """Hash the incoming key and compare against stored hashes."""
        incoming_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return any(
            hmac.compare_digest(incoming_hash, stored_hash)
            for stored_hash in self._valid_hashes.values()
        )

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # IMPORTANT: include={"authorization"} because get_http_headers()
        # strips the authorization header by default
        headers = get_http_headers(include={"authorization"}) or {}
        auth_header = headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            raise ToolError("Authentication required: missing or invalid Authorization header")

        raw_key = auth_header.removeprefix("Bearer ").strip()
        if not self._verify_key(raw_key):
            raise ToolError("Authentication failed: invalid API key")

        return await call_next(context)
```

### Pattern 2: RCARS HTTP Client with Retry and SA Token
**What:** httpx `AsyncClient` wrapper that handles SA token injection, exponential backoff retry, and structured error responses.
**When to use:** All RCARS API calls from MCP tools.
**Example:**
```python
# Source: httpx official docs (python-httpx.org) + D-04 retry spec
import asyncio
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

SA_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")


class RCARSClient:
    """Async HTTP client for RCARS API with retry and SA token auth."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _read_sa_token(self) -> str | None:
        """Re-read SA token from filesystem on every request (RCARS-01)."""
        try:
            return SA_TOKEN_PATH.read_text().strip()
        except FileNotFoundError:
            logger.warning("SA token not found at %s — running outside cluster?", SA_TOKEN_PATH)
            return None

    async def _request(
        self, method: str, path: str, *, json: dict | None = None,
        timeout: float | None = None, max_retries: int = 3,
    ) -> dict:
        """Execute request with exponential backoff retry (D-04)."""
        url = f"{self._base_url}{path}"
        delays = [1, 2, 4]  # exponential backoff
        last_error = None

        for attempt in range(max_retries):
            headers = {}
            sa_token = self._read_sa_token()
            if sa_token:
                headers["Authorization"] = f"Bearer {sa_token}"

            try:
                async with httpx.AsyncClient(timeout=timeout or self._timeout) as client:
                    response = await client.request(method, url, json=json, headers=headers)

                    if response.status_code < 400:
                        return response.json()
                    if response.status_code < 500:
                        # 4xx: fail fast (D-04)
                        raise RCARSError(
                            f"RCARS request failed ({response.status_code}): {response.text}",
                            status_code=response.status_code, retryable=False,
                        )
                    # 5xx: retryable
                    last_error = RCARSError(
                        f"RCARS server error ({response.status_code})",
                        status_code=response.status_code, retryable=True,
                    )
            except httpx.ConnectError as e:
                last_error = RCARSError(f"Connection to RCARS failed: {e}", retryable=True)
            except httpx.TimeoutException as e:
                last_error = RCARSError(f"RCARS request timed out: {e}", retryable=True)

            if attempt < max_retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(
                    "RCARS request failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, max_retries, delay, last_error,
                )
                await asyncio.sleep(delay)

        # D-05: moderate error verbosity
        raise RCARSError(
            f"RCARS {method} {path} failed after {max_retries} retries: {last_error}",
            retryable=False,
        )


class RCARSError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
```

### Pattern 3: Advisor Query with Poll Loop
**What:** Submit advisor query job, poll for result with timeout.
**When to use:** `ph_rcars_query` tool implementation.
**Example:**
```python
# Source: RCARS advisor.py routes (code-verified)
async def query_advisor(self, query: str, poll_interval: float = 3.0, timeout: float = 120.0) -> dict:
    """Submit query and poll until complete or timeout."""
    # Submit — RCARS uses stages=["prod"] by default, but design spec says prod_only=False
    result = await self._request("POST", "/api/v1/advisor/query", json={
        "query": query,
        "stages": ["prod", "dev", "event"],  # Full catalog per design spec
        "include_zt": True,
    })
    job_id = result["job_id"]

    # Poll
    elapsed = 0.0
    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        result = await self._request("GET", f"/api/v1/advisor/query/{job_id}/result")
        if result["status"] in ("completed", "failed"):
            return result

    return {"status": "timeout", "error": f"Advisor query timed out after {timeout}s", "result": None}
```

### Pattern 4: FastMCP 3.2+ Mount with Combined Lifespan
**What:** Mount FastMCP `http_app()` into existing FastAPI with combined lifespans.
**When to use:** Portal `main.py` update for v3 migration.
**Example:**
```python
# Source: Context7 /prefecthq/fastmcp — fastapi.mdx + lifespan.mdx
from fastmcp.utilities.lifespan import combine_lifespans

# Create MCP ASGI app (v3 uses http_app(), not streamable_http_app())
mcp_app = mcp_server.http_app(path="/")

# Combine portal lifespan with MCP lifespan
app = FastAPI(
    title="Publishing House Portal API",
    lifespan=combine_lifespans(lifespan, mcp_app.lifespan),
)

# Mount at /mcp
app.mount("/mcp", mcp_app)
```

### Anti-Patterns to Avoid
- **DO NOT use `get_http_headers()` without `include={"authorization"}`:** The default strips the `authorization` header. This is the most likely auth bug. [VERIFIED: Context7 fastmcp-server-dependencies.mdx]
- **DO NOT cache the SA token at startup:** RCARS-01 requires re-reading from filesystem on every request. K8s rotates tokens automatically. Caching causes stale tokens. [VERIFIED: design spec]
- **DO NOT use `ToolError` for HTTP 401 status codes:** `ToolError` returns MCP-level errors, not HTTP 401. For the MCP protocol, this is correct -- the client gets an error response. But the integration spec says "rejected with 401." In practice, FastMCP's `ToolError` in middleware sends an MCP error, and the transport-level 401 would require a different mechanism. The middleware `ToolError` approach is the officially documented pattern. [VERIFIED: Context7]
- **DO NOT build separate httpx clients per tool call:** Use the RCARS client class to share configuration (base URL, timeout, retry policy). Each call reads a fresh SA token, but client config is centralized.
- **DO NOT add RCARS health check to K8s liveness/readiness probes:** The existing probes hit `/api/v1/health`. The RCARS probe should be in the response body as a sub-check, not a gate. If RCARS is down, PH should still serve (graceful degradation). [ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key auth middleware | Custom ASGI middleware | FastMCP `Middleware` subclass with `on_call_tool` | Tool-level granularity, officially documented pattern, operates at MCP protocol level not HTTP level. [VERIFIED: Context7] |
| Timing-safe string comparison | `==` operator | `hmac.compare_digest()` | Prevents timing attacks on API key comparison. stdlib, zero dependencies. [VERIFIED: Python docs] |
| SHA-256 hashing | Custom hash function | `hashlib.sha256()` | stdlib, battle-tested, exact algorithm specified in design. [VERIFIED: design spec] |
| HTTP retry with backoff | Custom retry loop | httpx + manual asyncio.sleep (or tenacity) | httpx doesn't have built-in retry. Manual loop is 15 lines and matches D-04 exactly. Tenacity is overkill for 3 retries. [ASSUMED] |
| YAML parsing for keys file | Custom parser | `yaml.safe_load()` from PyYAML (already in deps) | Already in requirements.txt. Handles the `key-name: sha256:hash` format. [VERIFIED: requirements.txt] |
| Lifespan combination | Manual lifespan merging | `combine_lifespans()` from fastmcp.utilities | Official utility for exactly this problem. [VERIFIED: Context7] |

**Key insight:** The most complex pieces (MCP auth, HTTP resilience, YAML parsing) are all solved by existing libraries or stdlib. The custom code is glue: reading a file, hashing a string, polling a job.

## Common Pitfalls

### Pitfall 1: get_http_headers() Strips Authorization by Default
**What goes wrong:** API key middleware calls `get_http_headers()` and gets an empty dict for the authorization header. All requests fail auth.
**Why it happens:** FastMCP strips `authorization`, `host`, and `content-length` by default to prevent accidental forwarding to downstream services.
**How to avoid:** Always use `get_http_headers(include={"authorization"})` in auth middleware.
**Warning signs:** All tool calls return "Authentication required" even with valid Bearer token.
[VERIFIED: Context7 fastmcp-server-dependencies.mdx]

### Pitfall 2: FastMCP v2 to v3 streamable_http_app() Rename
**What goes wrong:** `mcp.streamable_http_app()` is removed in v3; code fails at import time.
**Why it happens:** FastMCP v3 renamed to `mcp.http_app()`. The existing code has a try/except fallback, but after upgrading to 3.2+, the old method is gone entirely.
**How to avoid:** Replace `streamable_http_app()` with `http_app()` and add `combine_lifespans` for the FastAPI lifespan integration.
**Warning signs:** `AttributeError: FastMCP has no attribute streamable_http_app`.
[VERIFIED: Context7 upgrading/from-fastmcp-2.mdx]

### Pitfall 3: RCARS Auth is X-Forwarded-Email, NOT Bearer Token
**What goes wrong:** PH backend sends `Authorization: Bearer <sa-token>` but RCARS expects `X-Forwarded-Email` (or a dev_user override). All RCARS calls get 401.
**Why it happens:** RCARS was built for browser access behind an OAuth proxy that sets `X-Forwarded-Email`. It has `sa_allowlist_str` in config but NO middleware that reads Bearer tokens and validates them via TokenReview.
**How to avoid:** Must build SA token auth middleware in RCARS (`rcars-advisory` repo) before PH can authenticate. Alternatively, use `RCARS_DEV_USER` as a temporary bypass during development (NOT for production).
**Warning signs:** RCARS returns 401 "Authentication required" despite valid SA token in header.
[VERIFIED: codebase -- rcars-advisory/src/api/rcars/api/middleware/auth.py lines 7-14]

### Pitfall 4: RCARS Advisor Query is Async (Job-Based)
**What goes wrong:** Developer tries to get results from the POST response and gets only `{job_id}`.
**Why it happens:** RCARS enqueues recommendation jobs to arq (Redis task queue). POST returns immediately with a job_id. Results come from a separate GET endpoint after the job completes.
**How to avoid:** Implement poll loop: POST -> get job_id -> poll GET until status is "completed" or "failed".
**Warning signs:** MCP tool returns `{"job_id": "abc123"}` instead of actual results.
[VERIFIED: codebase -- rcars-advisory/src/api/rcars/api/routes/advisor.py lines 26-42, 51-61]

### Pitfall 5: FastMCP v3 Lifespan Must Be Combined
**What goes wrong:** MCP tools work initially but sessions don't clean up, causing memory leaks or connection issues.
**Why it happens:** FastMCP v3 requires its lifespan to be properly initialized for session management. Mounting without `combine_lifespans` means the MCP server's startup/shutdown hooks never run.
**How to avoid:** Use `combine_lifespans(app_lifespan, mcp_app.lifespan)` when creating the FastAPI app.
**Warning signs:** Slow memory growth, "session not found" errors after extended runtime.
[VERIFIED: Context7 -- lifespan.mdx and fastapi.mdx both document this requirement]

### Pitfall 6: Volume-Mounted Secret File Path
**What goes wrong:** API key file not found at expected path; auth fails with "no valid keys loaded."
**Why it happens:** K8s volume mounts create the file at the mount path, but the exact path depends on the Secret's key name and the Deployment's volumeMount configuration. The key name in the Secret (`keys.yaml`) becomes the filename under the mount path.
**How to avoid:** Match the volumeMount mountPath + subPath with the Settings config field. Test locally with a mock file first.
**Warning signs:** FileNotFoundError on startup, empty `_valid_hashes` dict.
[ASSUMED]

## Code Examples

### RCARS API Endpoints (Verified from Codebase)

```python
# Source: rcars-advisory/src/api/rcars/api/routes/advisor.py (code-verified)

# 1. Submit advisor query
# POST /api/v1/advisor/query
# Body: {"query": "...", "stages": ["prod", "dev", "event"], "include_zt": true}
# Auth: require_auth (X-Forwarded-Email or dev_user -- must add SA auth)
# Response: {"job_id": "<uuid>"}

# 2. Poll for result
# GET /api/v1/advisor/query/{job_id}/result
# Auth: require_auth
# Response: {"status": "completed|pending|failed", "result": {...}, "error": "..."}

# 3. Stream progress (optional, not needed for MCP tool)
# GET /api/v1/advisor/query/{job_id}/stream
# Response: SSE stream
```

```python
# Source: rcars-advisory/src/api/rcars/api/routes/catalog.py (code-verified)

# 4. List catalog items
# GET /api/v1/catalog?limit=50&offset=0&stage=prod&category=workshop
# Auth: require_auth
# Response: {"items": [...], "total": 42}

# 5. Get single catalog item
# GET /api/v1/catalog/{ci_name}
# Auth: require_auth
# Response: {**item, "analysis": {...}, "tags": [...]}

# 6. Health check (NO auth required)
# GET /api/v1/health
# Response: {"status": "ok"}
```

### Existing Tool Pattern (Follow This)
```python
# Source: portal-backend/app/mcp/tools.py (code-verified)
# Existing tools use @mcp.tool() decorator and manage their own sessions.
# RCARS tools follow the same pattern but use httpx instead of DB sessions.

from app.mcp.server import mcp
from app.services.rcars_client import RCARSClient, RCARSError
from app.core.config import settings

@mcp.tool()
async def ph_rcars_query(query: str) -> dict:
    """Submit a content vetting query to RCARS and return matching catalog items
    with relevance tiers and rationale.

    Args:
        query: Natural language description combining learning objectives,
               topics, and products for the content being vetted.
    """
    client = RCARSClient(base_url=settings.rcars_internal_url)
    try:
        result = await client.query_advisor(query)
        return result
    except RCARSError as e:
        return {"error": str(e), "status": "unavailable"}
```

### Ansible Template for MCP Route and Secret
```yaml
# Source: Follows existing pattern in manifests-infra.yaml.j2 (code-verified)

# MCP external Route (only /mcp path exposed)
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ app_name }}-mcp
  labels:
    app: {{ app_name }}
spec:
  host: "{{ mcp_route_host }}"
  path: /mcp
  to:
    kind: Service
    name: {{ app_name }}-backend
  port:
    targetPort: {{ backend_port }}
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
---
# MCP API key Secret (volume-mounted into backend pod)
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-mcp-api-keys
  labels:
    app: {{ app_name }}
type: Opaque
stringData:
  keys.yaml: |
{% for key in mcp_api_keys | default({}) | dict2items %}
    {{ key.key }}: "sha256:{{ key.value }}"
{% endfor %}
```

### Intake Skill Replacement
```markdown
# Source: skills-plugin/skills/intake/SKILL.md lines 216-260 (code-verified)
# BEFORE (broken):
# curl -s -X POST "${RCARS_API}/recommend" ...

# AFTER:
## Phase 2: Vetting (RCARS)

### Check MCP Tool Availability

1. **Check if `ph_rcars_query` MCP tool is available**
   - If available: proceed to vetting
   - If unavailable (no MCP server configured, no API key):
     - Ask: "RCARS vetting requires the Publishing House MCP server.
       Should we skip vetting for now?"
     - If skip: set `lifecycle.phases.vetting.status: skipped` in manifest
     - Proceed to Phase 3

### Run Vetting Query

**Build query from spec:**
- Extract learning objectives
- Extract topics and products
- Combine into concise query string

**Call MCP tool:**
Use the `ph_rcars_query` tool with the combined query string.
The tool handles submission, polling, and structured result formatting.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastMCP 2.x `streamable_http_app()` | FastMCP 3.x `http_app()` | FastMCP 3.0.0 | Mount method renamed; must update `main.py` |
| FastMCP 2.x: no middleware support | FastMCP 3.x: `Middleware` class with `on_call_tool` | FastMCP 3.0.0 | Enables per-tool auth without custom ASGI middleware |
| No lifespan management for mounted MCP | `combine_lifespans()` utility | FastMCP 3.0.0 | Required for proper session cleanup in FastAPI integration |
| `get_tools()` returns dict | `list_tools()` returns list | FastMCP 3.0.0 | Breaking change if any code inspects registered tools |
| RCARS `/recommend` endpoint (v1) | RCARS `/api/v1/advisor/query` + poll (v2) | RCARS v2.0 | Job-based async model replaces synchronous recommend |

**Deprecated/outdated:**
- `FastMCP.streamable_http_app()`: removed in v3, use `http_app()` [VERIFIED: Context7]
- `WSTransport`: removed in v3, use `StreamableHttpTransport` (irrelevant for server-side but good to know) [VERIFIED: Context7]
- RCARS `/recommend` endpoint: does not exist in v2. The intake skill's curl call to this endpoint is the root cause of the broken vetting. [VERIFIED: no `/recommend` route in RCARS codebase]

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RCARS health check should not be a gate on PH liveness/readiness probes | Anti-Patterns | If RCARS availability SHOULD gate PH readiness, the K8s probes need updating. Low risk -- graceful degradation is explicitly required. |
| A2 | Manual retry loop is preferable to tenacity for 3-retry backoff | Don't Hand-Roll | If more complex retry logic is needed later, tenacity could be added. No risk for Phase 1 scope. |
| A3 | Volume-mounted Secret file path pitfall | Common Pitfalls | If the volume mount is configured differently than documented, file path will differ. Resolved during Ansible template implementation. |

## Open Questions

1. **Exact PH backend ServiceAccount name**
   - What we know: Backend deployment exists in `publishing-house-dev` namespace. The deployment template does NOT specify a custom serviceAccountName for the backend container (only the frontend has one for OAuth proxy). This means it uses the `default` SA.
   - What's unclear: Is the default SA name `default` or was a custom SA created during initial setup?
   - Recommendation: Check with `oc get deployment ph-dashboard-backend -o jsonpath='{.spec.template.spec.serviceAccountName}'` in the cluster. The allowlist entry format is `system:serviceaccount:publishing-house-dev:<sa-name>`.
   - [VERIFIED: codebase -- manifests-app.yaml.j2 shows no serviceAccountName for backend container]

2. **RCARS SA Token Auth Middleware -- Build vs. Bypass**
   - What we know: RCARS has `sa_allowlist_str` in config but NO middleware that validates SA tokens. Current auth is `X-Forwarded-Email` from OAuth proxy.
   - What's unclear: How much new RCARS code is acceptable in Phase 1? Building TokenReview middleware is a meaningful RCARS code change.
   - Recommendation: Build a lightweight SA auth dependency in RCARS that checks `Authorization: Bearer` for SA tokens, validates via K8s TokenReview API, and checks against the allowlist. This is ~50 lines of code. Alternatively, use `RCARS_DEV_USER` env var as an interim bypass while SA auth is built.
   - [VERIFIED: codebase -- no SA validation middleware exists]

3. **RCARS QueryRequest `stages` parameter default behavior**
   - What we know: RCARS `QueryRequest` defaults to `stages: ["prod"]`. Design spec says `prod_only=False` (full catalog picture).
   - What's unclear: Should PH always send all stages, or should this be configurable?
   - Recommendation: Hard-code `stages: ["prod", "dev", "event"]` in the MCP tool to match design spec intent. This ensures vetting sees the full catalog.
   - [VERIFIED: codebase -- advisor.py QueryRequest defaults to `["prod"]`]

4. **NetworkPolicy between publishing-house-dev and rcars-dev**
   - What we know: Both namespaces exist on the same cluster. RCARS API is ClusterIP service.
   - What's unclear: Whether restrictive NetworkPolicies block cross-namespace traffic.
   - Recommendation: Include a connectivity smoke test in the Ansible deploy or as a manual verification step. Cannot check from local machine.
   - [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend runtime | N/A (runs on cluster) | N/A | N/A -- cluster build uses Containerfile |
| OpenShift cluster | Deployment | N/A (remote) | N/A | Cannot run locally for full integration |
| RCARS API | MCP tools | N/A (remote service) | v2.0 | Graceful degradation in tools |
| rcars-advisory repo | RCARS auth changes | Yes (local clone) | main branch | -- |
| rhdp-publishing-house-portal repo | Portal backend changes | Yes (local clone) | gsd-project branch | -- |
| skills-plugin submodule | Intake skill changes | Yes (submodule) | gsd-project branch | -- |

**Missing dependencies with no fallback:**
- None -- all repos are available locally. Cluster deployment is manual (D-08).

**Missing dependencies with fallback:**
- Cannot verify cross-namespace connectivity from local machine. Fallback: document the verification steps for the user to run post-deploy.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `src/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd /Users/nstephan/devel/publishing-house/rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd /Users/nstephan/devel/publishing-house/rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | MCP endpoint accessible with valid API key | integration | `pytest tests/test_mcp_auth.py::test_valid_api_key -x` | Wave 0 |
| MCP-02 | Middleware validates on every tool call | unit | `pytest tests/test_mcp_auth.py::test_middleware_intercepts_all_tools -x` | Wave 0 |
| MCP-03 | Invalid key returns error; valid key proceeds | unit | `pytest tests/test_mcp_auth.py::test_invalid_key_rejected -x` | Wave 0 |
| MCP-04 | ph_rcars_query returns structured results | unit | `pytest tests/test_rcars_tools.py::test_query_tool -x` | Wave 0 |
| MCP-05 | ph_rcars_catalog_search returns paginated results | unit | `pytest tests/test_rcars_tools.py::test_catalog_search -x` | Wave 0 |
| MCP-06 | ph_rcars_catalog_item returns full metadata | unit | `pytest tests/test_rcars_tools.py::test_catalog_item -x` | Wave 0 |
| MCP-07 | Health endpoint reports RCARS status | unit | `pytest tests/test_health.py::test_health_rcars_status -x` | Wave 0 |
| MCP-08 | Ansible template renders Route + Secret | manual-only | N/A -- Ansible template validation requires cluster | N/A |
| RCARS-01 | SA token re-read from filesystem | unit | `pytest tests/test_rcars_client.py::test_sa_token_reread -x` | Wave 0 |
| RCARS-02 | RCARS validates SA token via TokenReview | manual-only | Requires RCARS cluster deployment | N/A |
| RCARS-03 | SA in RCARS allowlist | manual-only | Requires RCARS cluster deployment | N/A |
| RCARS-04 | Cross-namespace connectivity | manual-only | `curl` from PH pod to RCARS service | N/A |
| RCARS-05 | Intake skill uses ph_rcars_query | manual-only | Run intake skill in Claude Code session | N/A |

### Sampling Rate
- **Per task commit:** `cd /Users/nstephan/devel/publishing-house/rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd /Users/nstephan/devel/publishing-house/rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mcp_auth.py` -- covers MCP-01, MCP-02, MCP-03 (API key auth middleware)
- [ ] `tests/test_rcars_tools.py` -- covers MCP-04, MCP-05, MCP-06 (RCARS MCP tools with mocked httpx)
- [ ] `tests/test_rcars_client.py` -- covers RCARS-01, D-04 retry logic (RCARS HTTP client)
- [ ] Update `tests/test_health.py` -- covers MCP-07 (add RCARS status sub-check)
- [ ] Framework install: already available (`pytest>=8.0` in requirements.txt)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | API key auth (SHA-256 + hmac.compare_digest) for external MCP; SA token + TokenReview for cluster-internal RCARS |
| V3 Session Management | No | MCP is stateless per-request; no sessions to manage |
| V4 Access Control | Yes | All MCP tools gated by ApiKeyAuth middleware; RCARS tools additionally require SA token |
| V5 Input Validation | Yes | Pydantic models for RCARS request/response schemas; query string sanitization |
| V6 Cryptography | Yes | SHA-256 for API key hashing (hashlib.sha256, stdlib -- never hand-roll) |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key timing attack | Information Disclosure | `hmac.compare_digest()` for constant-time comparison |
| API key in logs | Information Disclosure | Never log raw keys; log key name (admin identifier) only |
| SA token theft via pod compromise | Spoofing | Short-lived K8s projected SA tokens (auto-rotated); RCARS validates via TokenReview |
| RCARS response injection | Tampering | Validate RCARS response structure with Pydantic before returning to MCP client |
| Unauthenticated health endpoint | Information Disclosure | `/health` is intentionally unauthenticated (D-06) but reveals only connectivity status, not data |
| Volume-mounted Secret file permissions | Information Disclosure | K8s sets 0644 by default; `defaultMode: 0400` in volume spec for read-only by pod user |

## Sources

### Primary (HIGH confidence)
- [Context7 /prefecthq/fastmcp v3.2.4] - Middleware auth pattern, `get_http_headers()` behavior, `combine_lifespans()`, `http_app()` mount pattern, v2-to-v3 migration guide
- [PyPI fastmcp] - v3.2.4 verified current (April 2026)
- [PyPI httpx] - v0.28.1 verified current
- [Codebase: rcars-advisory/src/api/rcars/api/routes/advisor.py] - RCARS advisor API contract (POST query, GET result, job-based async model)
- [Codebase: rcars-advisory/src/api/rcars/api/routes/catalog.py] - RCARS catalog API contract (GET list, GET item)
- [Codebase: rcars-advisory/src/api/rcars/api/middleware/auth.py] - RCARS auth model (X-Forwarded-Email, NOT SA token -- critical finding)
- [Codebase: rcars-advisory/src/api/rcars/config.py] - `sa_allowlist_str` config exists but unused
- [Codebase: rhdp-publishing-house-portal/src/backend/app/mcp/server.py] - Current FastMCP 2.0 setup with Keycloak scaffolding
- [Codebase: rhdp-publishing-house-portal/src/backend/app/mcp/tools.py] - Existing tool pattern (@mcp.tool, SessionLocal)
- [Codebase: rhdp-publishing-house-portal/src/backend/app/main.py] - Current MCP mount with streamable_http_app fallback
- [Codebase: rhdp-publishing-house-portal/ansible/templates/manifests-infra.yaml.j2] - Existing Ansible Secret/Route template patterns
- [Codebase: rhdp-publishing-house-portal/ansible/templates/manifests-app.yaml.j2] - Backend deployment (no custom SA, RCARS_URL env var pattern)
- [Codebase: rcars-advisory/ansible/templates/manifests-app.yaml.j2] - RCARS deployment (no SA_ALLOWLIST_STR env var yet)

### Secondary (MEDIUM confidence)
- [Design spec: docs/superpowers/specs/2026-04-27-rcars-integration-design.md] - Auth model, tool contracts, deployment changes, verification checklist

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or Context7

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- versions verified via PyPI, APIs verified via codebase
- Architecture: HIGH -- all integration points examined in actual code
- Pitfalls: HIGH -- each pitfall traced to specific code or documentation evidence
- RCARS SA auth gap: HIGH -- verified by reading actual RCARS middleware code (no SA validation exists)

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (stable -- dependencies are established, RCARS API is deployed)
