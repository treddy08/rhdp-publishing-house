# Phase 1: RCARS MCP Gateway - Pattern Map

**Mapped:** 2026-04-30
**Files analyzed:** 14 new/modified files across 4 repos
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `portal:app/mcp/auth.py` | middleware | request-response | `portal:app/mcp/auth.py` (self - REPLACE) | exact |
| `portal:app/mcp/server.py` | config | request-response | `portal:app/mcp/server.py` (self - MODIFY) | exact |
| `portal:app/mcp/rcars_tools.py` | controller | request-response | `portal:app/mcp/tools.py` | exact |
| `portal:app/services/rcars_client.py` | service | request-response | `portal:app/services/github_client.py` | role-match |
| `portal:app/core/config.py` | config | n/a | `portal:app/core/config.py` (self - MODIFY) | exact |
| `portal:app/api/health.py` | controller | request-response | `portal:app/api/health.py` (self - MODIFY) | exact |
| `portal:app/main.py` | config | n/a | `portal:app/main.py` (self - MODIFY) | exact |
| `portal:tests/test_mcp_auth.py` | test | n/a | `portal:tests/test_github_client.py` | role-match |
| `portal:tests/test_rcars_tools.py` | test | n/a | `portal:tests/test_github_client.py` | role-match |
| `portal:tests/test_rcars_client.py` | test | n/a | `portal:tests/test_github_client.py` | role-match |
| `portal:ansible/templates/manifests-infra.yaml.j2` | config | n/a | `portal:ansible/templates/manifests-infra.yaml.j2` (self - MODIFY) | exact |
| `portal:ansible/templates/manifests-app.yaml.j2` | config | n/a | `portal:ansible/templates/manifests-app.yaml.j2` (self - MODIFY) | exact |
| `rcars:src/api/rcars/api/middleware/auth.py` | middleware | request-response | `rcars:src/api/rcars/api/middleware/auth.py` (self - MODIFY) | exact |
| `skills:skills/intake/SKILL.md` | utility | n/a | `skills:skills/intake/SKILL.md` (self - MODIFY) | exact |

**Repo key:** `portal` = `rhdp-publishing-house-portal`, `rcars` = `rcars-advisory`, `skills` = `skills-plugin` (submodule in `rhdp-publishing-house`)

## Pattern Assignments

### `portal:app/mcp/auth.py` (middleware, request-response) -- REPLACE

**Analog:** `portal:app/mcp/auth.py` (current Keycloak scaffolding, to be fully replaced with FastMCP Middleware API key auth)

**Current file** (`rhdp-publishing-house-portal/src/backend/app/mcp/auth.py` lines 1-88):
The entire file is the `KeycloakTokenVerifier` class. Delete all content and replace with the `ApiKeyAuth(Middleware)` subclass.

**New pattern source:** FastMCP 3.2+ Middleware (from RESEARCH.md Pattern 1, Context7-verified)

**Imports pattern:**
```python
import hashlib
import hmac
import logging
from pathlib import Path

import yaml
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError
```

**Core pattern** -- API key validation middleware:
```python
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
        # CRITICAL: include={"authorization"} -- get_http_headers() strips auth by default
        headers = get_http_headers(include={"authorization"}) or {}
        auth_header = headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            raise ToolError("Authentication required: missing or invalid Authorization header")

        raw_key = auth_header.removeprefix("Bearer ").strip()
        if not self._verify_key(raw_key):
            raise ToolError("Authentication failed: invalid API key")

        return await call_next(context)
```

**Error handling pattern:**
```python
# Uses ToolError from fastmcp.exceptions -- NOT HTTPException
# ToolError is the MCP-protocol-level error mechanism
raise ToolError("Authentication required: missing or invalid Authorization header")
raise ToolError("Authentication failed: invalid API key")
```

---

### `portal:app/mcp/server.py` (config, request-response) -- MODIFY

**Analog:** `portal:app/mcp/server.py` (self, `rhdp-publishing-house-portal/src/backend/app/mcp/server.py` lines 1-47)

**Current imports pattern** (lines 1-5):
```python
import logging

from fastmcp import FastMCP

from app.core.config import settings
```

**Current core pattern** (lines 9-16):
```python
mcp = FastMCP(
    name="publishing-house",
    instructions=(
        "Publishing House portal MCP server. Provides cross-project visibility, "
        "launch instructions, and validation result storage for RHDP content "
        "lifecycle projects."
    ),
)
```

**What changes:** Remove entire Keycloak auth scaffolding block (lines 18-47). Add `ApiKeyAuth` middleware to the `FastMCP` constructor. The `FastMCP()` constructor in v3.2+ accepts a `middleware` parameter.

**New pattern:**
```python
import logging
from pathlib import Path

from fastmcp import FastMCP

from app.core.config import settings
from app.mcp.auth import ApiKeyAuth

logger = logging.getLogger(__name__)

# API key auth middleware (reads keys from volume-mounted Secret)
_middleware = []
if settings.mcp_api_key_file:
    keys_path = Path(settings.mcp_api_key_file)
    if keys_path.exists():
        _middleware.append(ApiKeyAuth(keys_file=keys_path))
        logger.info("MCP API key auth enabled — keys loaded from %s", keys_path)
    else:
        logger.warning("MCP API key file not found at %s — auth disabled", keys_path)

mcp = FastMCP(
    name="publishing-house",
    instructions=(
        "Publishing House portal MCP server. Provides cross-project visibility, "
        "launch instructions, validation result storage, and RCARS content advisory "
        "tools for RHDP content lifecycle projects."
    ),
    middleware=_middleware,
)
```

---

### `portal:app/mcp/rcars_tools.py` (controller, request-response) -- NEW

**Analog:** `portal:app/mcp/tools.py` (`rhdp-publishing-house-portal/src/backend/app/mcp/tools.py` lines 1-175)

**Imports pattern** (lines 1-16):
```python
"""MCP tools for the Publishing House portal.

Each tool manages its own DB session via SessionLocal() since
MCP tools run outside the FastAPI request lifecycle.
"""
from __future__ import annotations

from typing import Optional

from app.core.database import SessionLocal
from app.mcp.server import mcp
from app.models.manifest import Manifest
from app.models.phase import Phase
from app.models.project import Project
from app.models.validation import ValidationRun
from app.services.launch_instructions import get_launch_instructions
```

**Adaptation for RCARS tools** -- replace DB imports with RCARS client:
```python
"""RCARS MCP tools for content advisory queries.

Each tool instantiates its own RCARSClient since MCP tools run
outside the FastAPI request lifecycle.
"""
from __future__ import annotations

from app.mcp.server import mcp
from app.services.rcars_client import RCARSClient, RCARSError
from app.core.config import settings
```

**Core tool pattern** (follow `tools.py` lines 19-54 for decorator + docstring + error handling):
```python
@mcp.tool()
def ph_list_projects() -> list[dict]:
    """List all Publishing House projects with their current phase and status.

    Returns a summary for each project including name, repo_url,
    current phase, and deployment_mode.
    """
    db = SessionLocal()
    try:
        # ... business logic ...
        return results
    finally:
        db.close()
```

**Adaptation for RCARS tools** -- async, httpx instead of DB, graceful degradation:
```python
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

**Error handling pattern** (from `tools.py` lines 67-69):
```python
if not project:
    return {"error": f"Project {project_id} not found"}
```
RCARS tools use the same dict-based error return, not exceptions -- MCP clients receive structured error data:
```python
except RCARSError as e:
    return {"error": str(e), "status": "unavailable"}
```

---

### `portal:app/services/rcars_client.py` (service, request-response) -- NEW

**Analog:** `portal:app/services/github_client.py` (`rhdp-publishing-house-portal/src/backend/app/services/github_client.py` lines 1-189)

**Module docstring pattern** (line 1-3):
```python
"""GitHub client service.

Handles fetching manifest files from GitHub repositories.
"""
```

**Custom exception pattern** (lines 13-15):
```python
class GitHubFetchError(Exception):
    """Custom exception for GitHub fetch errors."""
    pass
```

**Adaptation for RCARS:**
```python
class RCARSError(Exception):
    """Custom exception for RCARS API errors."""
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
```

**HTTP request pattern with httpx** (lines 69-84):
```python
headers = {
    "Accept": "application/vnd.github.v3+json",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

url = f"https://api.github.com/repos/{owner}/{repo}"
response = httpx.get(url, headers=headers, timeout=15)

if response.status_code == 200:
    data = response.json()
    return data.get("pushed_at")

raise GitHubFetchError(
    f"Failed to fetch repo metadata for {owner}/{repo}. HTTP {response.status_code}"
)
```

**Adaptation for RCARS** -- async httpx with retry + SA token:
```python
async def _request(self, method: str, path: str, *, json: dict | None = None,
                   timeout: float | None = None, max_retries: int = 3) -> dict:
    url = f"{self._base_url}{path}"
    delays = [1, 2, 4]  # exponential backoff per D-04
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
                    raise RCARSError(f"RCARS request failed ({response.status_code})",
                                    status_code=response.status_code, retryable=False)
                last_error = RCARSError(f"RCARS server error ({response.status_code})",
                                        status_code=response.status_code, retryable=True)
        except httpx.ConnectError as e:
            last_error = RCARSError(f"Connection to RCARS failed: {e}", retryable=True)
        except httpx.TimeoutException as e:
            last_error = RCARSError(f"RCARS request timed out: {e}", retryable=True)

        if attempt < max_retries - 1:
            delay = delays[min(attempt, len(delays) - 1)]
            logger.warning("RCARS request failed (attempt %d/%d), retrying in %ds: %s",
                           attempt + 1, max_retries, delay, last_error)
            await asyncio.sleep(delay)

    raise RCARSError(f"RCARS {method} {path} failed after {max_retries} retries: {last_error}",
                     retryable=False)
```

**Error message verbosity** -- follows `github_client.py` pattern of including context in error strings (lines 82-84, 139-142):
```python
raise GitHubFetchError(
    f"Failed to fetch repo metadata for {owner}/{repo}. HTTP {response.status_code}"
)
raise GitHubFetchError(
    f"Failed to fetch manifest from {owner}/{repo}. Tried: {tried}. Last error: {last_error}"
)
```

---

### `portal:app/core/config.py` (config) -- MODIFY

**Analog:** `portal:app/core/config.py` (self, `rhdp-publishing-house-portal/src/backend/app/core/config.py` lines 1-21)

**Current full file:**
```python
from typing import Optional

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str  # Required -- set via DATABASE_URL env var
    github_token: str = ""
    debug: bool = False
    refresh_hour: int = 2  # Nightly refresh at 2 AM (legacy, kept for reference)
    refresh_interval_minutes: int = 30  # Interval-based refresh every N minutes

    # External tool URLs (shown in sidebar navigation)
    rcars_url: Optional[str] = None  # e.g. https://rcars-dev.apps.example.com/

    # MCP authentication (Keycloak JWT) -- disabled by default
    mcp_auth_enabled: bool = False
    keycloak_realm_url: Optional[str] = None  # e.g. https://sso.example.com/realms/myrealm

    model_config = {"env_prefix": "", "env_file": ".env"}

settings = Settings()
```

**Changes needed:**
1. Remove `mcp_auth_enabled` and `keycloak_realm_url` (Keycloak scaffolding)
2. Add `rcars_internal_url` for cluster-internal RCARS API base URL
3. Add `mcp_api_key_file` for the volume-mounted Secret file path

**Pattern for new settings fields** (follow existing `Optional[str] = None` with comment style):
```python
    # RCARS cluster-internal API (cross-namespace)
    rcars_internal_url: str = "http://rcars-api.rcars-dev.svc.cluster.local:8080"

    # MCP API key auth (volume-mounted Secret file path)
    mcp_api_key_file: Optional[str] = None  # e.g. /etc/ph/mcp-api-keys/keys.yaml
```

---

### `portal:app/api/health.py` (controller, request-response) -- MODIFY

**Analog:** `portal:app/api/health.py` (self, `rhdp-publishing-house-portal/src/backend/app/api/health.py` lines 1-28)

**Current full file:**
```python
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


class HealthResponse(BaseModel):
    status: str


class PublicConfigResponse(BaseModel):
    rcars_url: Optional[str] = None


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok"}


@router.get("/config", response_model=PublicConfigResponse)
def get_public_config():
    """Public configuration for the frontend (external tool URLs, feature flags)."""
    return {"rcars_url": settings.rcars_url}
```

**Changes needed:**
1. Add RCARS connectivity sub-check to health response (D-06: actively probe RCARS)
2. Expand `HealthResponse` model to include RCARS status
3. Keep K8s liveness/readiness probes unaffected (RCARS down should NOT fail the probe -- graceful degradation)

**Extended response model pattern:**
```python
class HealthResponse(BaseModel):
    status: str
    rcars: Optional[dict] = None  # {"status": "ok"} or {"status": "unavailable", "error": "..."}
```

---

### `portal:app/main.py` (config) -- MODIFY

**Analog:** `portal:app/main.py` (self, `rhdp-publishing-house-portal/src/backend/app/main.py` lines 1-66)

**Current MCP mount pattern** (lines 60-65):
```python
# Mount MCP as HTTP (requires fastmcp, Python >=3.10)
if _mcp_available:
    try:
        app.mount("/mcp", mcp_server.streamable_http_app())
    except AttributeError:
        app.mount("/mcp", mcp_server.http_app())
```

**New pattern (FastMCP 3.2+):**
```python
# Mount MCP as HTTP (FastMCP 3.2+)
if _mcp_available:
    from fastmcp.utilities.lifespan import combine_lifespans
    mcp_app = mcp_server.http_app(path="/")
    app = FastAPI(
        title="Publishing House Portal API",
        lifespan=combine_lifespans(lifespan, mcp_app.lifespan),
    )
    # ... CORS, routers ...
    app.mount("/mcp", mcp_app)
```

**Import change needed** (line 13):
```python
# OLD: from app.mcp.tools import mcp as mcp_server
# NEW: ensure rcars_tools is also imported to register RCARS tools
from app.mcp.tools import mcp as mcp_server  # registers DB tools
import app.mcp.rcars_tools  # registers RCARS tools (side-effect import)
```

---

### `portal:tests/test_mcp_auth.py` (test) -- NEW

**Analog:** `portal:tests/test_github_client.py` (`rhdp-publishing-house-portal/src/backend/tests/test_github_client.py` lines 1-105)

**Test structure pattern** (lines 1-8):
```python
import pytest
import base64
from unittest.mock import patch, MagicMock
from app.services.github_client import (
    parse_repo_url,
    fetch_manifest,
    GitHubFetchError,
)
```

**Test naming convention** -- `test_<function_name>_<scenario>`:
```python
def test_parse_repo_url_with_ssh_url():
def test_parse_repo_url_with_https_url():
def test_fetch_manifest_success(mock_httpx):
def test_fetch_manifest_404_error(mock_httpx):
```

**Mock pattern** (lines 50-52):
```python
@patch("app.services.github_client.httpx")
def test_fetch_manifest_success(mock_httpx):
```

**Conftest fixture pattern** (`tests/conftest.py` lines 1-37):
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture
def client(test_db):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Adaptation for MCP auth tests:**
```python
import pytest
from unittest.mock import patch, MagicMock
from app.mcp.auth import ApiKeyAuth
from pathlib import Path
import hashlib
import tempfile
import yaml

def test_verify_key_valid():
def test_verify_key_invalid():
def test_missing_auth_header():
def test_malformed_bearer_token():
def test_keys_file_not_found():
```

---

### `portal:tests/test_rcars_tools.py` (test) -- NEW

**Analog:** Same as above -- `portal:tests/test_github_client.py`

**Pattern:** Mock the `RCARSClient` at the module level, test each `@mcp.tool()` function directly.

---

### `portal:tests/test_rcars_client.py` (test) -- NEW

**Analog:** `portal:tests/test_github_client.py` (lines 50-105 for httpx mocking)

**httpx mock pattern** (lines 50-88):
```python
@patch("app.services.github_client.httpx")
def test_fetch_manifest_success(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": encoded_content,
        "encoding": "base64",
    }
    mock_httpx.get.return_value = mock_response

    result = fetch_manifest("owner", "repo", "test-token")
    assert result == manifest_content
```

**Error case pattern** (lines 91-105):
```python
@patch("app.services.github_client.httpx")
def test_fetch_manifest_404_error(mock_httpx):
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_httpx.get.return_value = mock_response

    with pytest.raises(GitHubFetchError) as exc_info:
        fetch_manifest("owner", "repo", "test-token")

    assert "404" in str(exc_info.value)
```

**Adaptation for RCARS client** -- async httpx requires `pytest-asyncio` and `AsyncMock`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
@patch("app.services.rcars_client.httpx.AsyncClient")
async def test_request_success(mock_client_cls):
    # ...

@pytest.mark.asyncio
async def test_retry_on_5xx():
    # ...

def test_sa_token_reread(tmp_path):
    # Test that SA token is read from filesystem on each request
```

---

### `portal:ansible/templates/manifests-infra.yaml.j2` (config) -- MODIFY

**Analog:** `portal:ansible/templates/manifests-infra.yaml.j2` (self, lines 1-281)

**Secret template pattern** (lines 28-65):
```yaml
---
# PostgreSQL credentials
apiVersion: v1
kind: Secret
metadata:
  name: {{ app_name }}-postgresql
  labels:
    app: {{ app_name }}
    component: postgresql
type: Opaque
stringData:
  POSTGRESQL_USER: "{{ pg_user }}"
  POSTGRESQL_PASSWORD: "{{ pg_password }}"
  POSTGRESQL_DATABASE: "{{ pg_database }}"
```

**New MCP API key Secret** -- follows same structure:
```yaml
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

**Route template pattern** (from `manifests-app.yaml.j2` lines 233-250):
```yaml
---
# Route
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ app_name }}
  labels:
    app: {{ app_name }}
  annotations:
    haproxy.router.openshift.io/timeout: 120s
spec:
  host: "{{ frontend_host }}"
  to:
    kind: Service
    name: {{ app_name }}-frontend
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

**New MCP Route** -- follows same structure, adds path restriction:
```yaml
---
# MCP external Route (only /mcp path exposed)
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
```

---

### `portal:ansible/templates/manifests-app.yaml.j2` (config) -- MODIFY

**Analog:** `portal:ansible/templates/manifests-app.yaml.j2` (self, lines 1-250)

**Env var injection pattern** (lines 53-79):
```yaml
          env:
            - name: PG_USER
              valueFrom:
                secretKeyRef:
                  name: {{ app_name }}-postgresql
                  key: POSTGRESQL_USER
{% if rcars_url is defined and rcars_url %}
            - name: RCARS_URL
              value: "{{ rcars_url }}"
{% endif %}
```

**New env vars to add** -- follows same conditional pattern:
```yaml
{% if rcars_internal_url is defined and rcars_internal_url %}
            - name: RCARS_INTERNAL_URL
              value: "{{ rcars_internal_url }}"
{% endif %}
{% if mcp_api_keys is defined %}
            - name: MCP_API_KEY_FILE
              value: /etc/ph/mcp-api-keys/keys.yaml
{% endif %}
```

**Volume mount pattern** (from `manifests-app.yaml.j2` lines 220-229, OAuth proxy Secret mount):
```yaml
          volumeMounts:
            - mountPath: /etc/proxy/secrets
              name: oauth-proxy-secret
              readOnly: true
      volumes:
        - name: oauth-proxy-secret
          secret:
            secretName: {{ app_name }}-oauth-proxy-secret
```

**New volume mount for MCP API keys:**
```yaml
{% if mcp_api_keys is defined %}
          volumeMounts:
            - name: mcp-api-keys
              mountPath: /etc/ph/mcp-api-keys
              readOnly: true
{% endif %}
      volumes:
{% if mcp_api_keys is defined %}
        - name: mcp-api-keys
          secret:
            secretName: {{ app_name }}-mcp-api-keys
            defaultMode: 0400
{% endif %}
```

---

### `rcars:src/api/rcars/api/middleware/auth.py` (middleware, request-response) -- MODIFY

**Analog:** `rcars:src/api/rcars/api/middleware/auth.py` (self, `/Users/nstephan/devel/rcars-advisory/src/api/rcars/api/middleware/auth.py` lines 1-38)

**Current auth dependency pattern** (lines 7-14):
```python
def get_current_user(request: Request) -> str:
    settings: Settings = request.app.state.settings
    if settings.dev_user:
        return settings.dev_user
    email = request.headers.get("X-Forwarded-Email", "")
    if not email:
        email = request.headers.get("X-Forwarded-User", "")
    return email
```

**Current require_auth pattern** (lines 17-21):
```python
def require_auth(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

**Changes needed:** Add SA token path to `get_current_user` -- if `Authorization: Bearer` is present and the SA is in the allowlist, return the SA identity. This keeps `require_auth` unchanged.

**New SA auth function** -- follows existing pattern of reading from `request.app.state.settings`:
```python
async def _validate_sa_token(request: Request, token: str) -> str | None:
    """Validate a ServiceAccount token via K8s TokenReview API."""
    # Use kubernetes client or httpx to call TokenReview
    # Check result against settings.sa_allowlist
    # Return SA identity string or None
```

---

### `rcars:ansible/templates/manifests-app.yaml.j2` (config) -- MODIFY

**Analog:** `rcars:ansible/templates/manifests-app.yaml.j2` (self, `/Users/nstephan/devel/rcars-advisory/ansible/templates/manifests-app.yaml.j2` lines 70-109)

**Env var pattern for role lists** (lines 102-109):
```yaml
            - name: RCARS_CURATOR_EMAILS_STR
              value: "{{ curator_emails | join(',') }}"
            - name: RCARS_ADMIN_EMAILS_STR
              value: "{{ admin_emails | join(',') }}"
            - name: RCARS_STALE_DAYS
              value: "{{ stale_days }}"
            - name: RCARS_DEV_USER
              value: ""
```

**New env var to add** -- follows exact same CSV join pattern:
```yaml
            - name: RCARS_SA_ALLOWLIST_STR
              value: "{{ sa_allowlist | default([]) | join(',') }}"
```

**Vars file addition** (`rcars:ansible/vars/dev.yml.example` and `dev.yml`):
Follow existing `curator_emails` list pattern (line 37-38):
```yaml
curator_emails:
  - your-email@redhat.com
```
Add:
```yaml
sa_allowlist:
  - "system:serviceaccount:publishing-house-dev:default"
```

---

### `skills:skills/intake/SKILL.md` (utility) -- MODIFY

**Analog:** `skills:skills/intake/SKILL.md` (self, lines 216-268)

**Current broken pattern** (lines 216-244):
```markdown
## Phase 2: Vetting (RCARS)

### Check RCARS Availability

1. **Read integrations.rcars_api from manifest**
   - If URL present: proceed to API call
   - If null/empty: ask user

2. **If RCARS unavailable:**
   - Ask: "Do you have an RCARS API endpoint URL, or should we skip vetting?"
   - If skip: set `lifecycle.phases.vetting.status: skipped` in manifest
   - Proceed to Phase 3

### Call RCARS API

**Make API call:**
```bash
curl -s -X POST "${RCARS_API}/recommend" \
  -H "Content-Type: application/json" \
  -d '{"query": "<learning objectives + topics + products>", "limit": 10}'
```
```

**Replacement** -- MCP tool reference instead of curl:
```markdown
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

---

## Shared Patterns

### Logging

**Source:** All portal backend files
**Apply to:** All new Python files (`auth.py`, `rcars_tools.py`, `rcars_client.py`)

```python
import logging

logger = logging.getLogger(__name__)
```

Used consistently across `server.py` (line 7), `github_client.py` (implicit via module pattern). All modules use `logger.warning()`, `logger.info()`, `logger.error()`.

### Pydantic Settings

**Source:** `portal:app/core/config.py` (lines 1-21)
**Apply to:** `config.py` modifications

```python
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # field: type = default  # comment explaining the field
    rcars_url: Optional[str] = None  # e.g. https://rcars-dev.apps.example.com/

    model_config = {"env_prefix": "", "env_file": ".env"}

settings = Settings()
```

Pattern: all config fields have defaults (except `database_url`). Optional fields use `Optional[str] = None`. Each field has an inline comment with an example value.

### httpx Usage

**Source:** `portal:app/services/github_client.py` (lines 69-84)
**Apply to:** `rcars_client.py`

Existing codebase uses **synchronous** httpx (`httpx.get()`). The RCARS client will use **async** httpx (`httpx.AsyncClient`). This is the first async httpx usage in the portal backend -- be aware that the MCP tool functions must be `async def` to use `await`.

### Ansible Jinja2 Template Conventions

**Source:** `portal:ansible/templates/manifests-infra.yaml.j2` + `manifests-app.yaml.j2`
**Apply to:** All Ansible template modifications

Conventions observed:
1. YAML doc separator `---` between each K8s resource
2. Comment line before each resource: `# Resource description`
3. Labels always include `app: {{ app_name }}`
4. Secrets use `stringData:` (not `data:` with base64)
5. Conditional blocks use `{% if var is defined and var %}` for optional resources
6. Volume mounts are `readOnly: true` for secrets
7. Security context: `allowPrivilegeEscalation: false`, `capabilities: drop: ["ALL"]`

### Test Conventions

**Source:** `portal:tests/` (all test files)
**Apply to:** All new test files

Conventions observed:
1. File naming: `test_<module_name>.py`
2. Function naming: `test_<function>_<scenario>()`
3. Mock pattern: `@patch("app.services.<module>.<dependency>")`
4. Mock response: `MagicMock()` with `.status_code` and `.json.return_value`
5. Error assertion: `with pytest.raises(ErrorClass) as exc_info:`
6. Fixtures from `conftest.py`: `client` (TestClient), `db_session`, `test_db` (autouse)
7. No class-based tests -- all standalone functions

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| *None* | -- | -- | All files have analogs in the existing codebase |

All 14 files either modify existing files (exact analog = self) or have close analogs in the same codebase layer. The RCARS client is the most novel file but closely follows the `github_client.py` service pattern with async adaptation.

---

## Metadata

**Analog search scope:**
- `rhdp-publishing-house-portal/src/backend/app/` (Python backend)
- `rhdp-publishing-house-portal/src/backend/tests/` (test files)
- `rhdp-publishing-house-portal/ansible/` (Ansible deployer)
- `rcars-advisory/src/api/rcars/` (RCARS backend)
- `rcars-advisory/ansible/` (RCARS deployer)
- `skills-plugin/skills/intake/` (intake skill)

**Files scanned:** 38 source files across 4 repositories
**Pattern extraction date:** 2026-04-30
