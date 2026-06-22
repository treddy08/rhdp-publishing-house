# MCP Server

## Overview

The Publishing House MCP server is the single gateway between Claude Code skills and all backend services. It runs inside the Central backend (FastAPI + FastMCP 3.4+), mounted at the `/mcp` endpoint. Every external integration — gate service, RCARS, Jira sync, project storage, validation, session continuity — flows through MCP tools. Skills never make raw HTTP calls to external services.

### Why MCP

Without the MCP server, every skill would need its own HTTP client, auth configuration, retry logic, and error handling for each backend service. The MCP server centralizes all of that: one endpoint, one auth model, one set of clients. Adding a new integration means adding a tool, not modifying every skill.

### Where It Runs

The MCP server is deployed on OpenShift as part of the Central backend pod in the `publishing-house-central-dev` namespace. It shares the FastAPI process — same deployment, same database, same service account.

| Component | Detail |
|-----------|--------|
| **Framework** | FastMCP 3.4+ mounted on FastAPI |
| **Endpoint** | `https://<mcp-route-host>/mcp` |
| **Auth** | API key (Bearer token, SHA-256 hashed, see [MCP Auth](../admin/mcp-auth.md)) |
| **Backend services accessed** | RCARS API (cluster-internal), Jira Cloud API, PostgreSQL, GitHub API |

### How Skills Connect

Claude Code users configure the MCP endpoint in their Claude Code settings. The PH skills plugin ships with the endpoint pre-configured. Skills call MCP tools through standard Claude Code tool invocation — no SDK, no HTTP library, just `@mcp.tool()` decorated functions.

For hosted workspaces (Dev Spaces), the MCP endpoint URL is injected as an environment variable at workspace creation.

### Tool Categories

The server exposes tools in four categories:

| Category | Tools | Purpose |
|----------|-------|---------|
| **Gate Service** | `ph_register`, `ph_get_status`, `ph_request_gate`, `ph_submit_results`, `ph_get_history`, `ph_get_open_initiatives`, `ph_list_projects` | Project registration, phase gates, custody chain, Jira initiatives |
| **RCARS Content Advisory** | `ph_rcars_query`, `ph_rcars_catalog_search`, `ph_rcars_catalog_item` | Content vetting, catalog browsing, item detail lookup |
| **Session Continuity** | `ph_store_intake_results`, `ph_get_intake_results`, `ph_list_intake_sessions`, `ph_record_express_run` | Intake persistence, express mode metrics |
| **Legacy** | `ph_get_launch_instructions`, `ph_store_validation_results`, `ph_get_validation_results`, `ph_sync_manifest` | Validation storage, manifest sync, launch instructions |

---

## Tools Reference

Detailed parameters, return shapes, and examples for each tool.

## RCARS Content Advisory Tools

These tools provide access to the RCARS v2 content advisory system through the PH MCP gateway. They require a valid API key (see [Claude Code Setup Guide](../user/claude-code-setup.md)).

---

### ph_rcars_query

Submit a content vetting query to the RCARS advisor. The tool submits the query, polls for results (up to 120 seconds), and returns structured matches with relevance tiers.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | Yes | Natural language description combining learning objectives, topics, and products for the content being vetted. |

#### Return Shape (success)

```json
{
  "status": "completed",
  "result": {
    "matches": [
      {
        "ci_name": "ocp4_getting_started",
        "display_name": "OpenShift 4 Getting Started",
        "stage": "prod",
        "tier": "green",
        "rationale": "Covers foundational OCP concepts including deployment, services, and routes."
      }
    ]
  }
}
```

**Field descriptions:**

| Field | Description |
|-------|-------------|
| `status` | Query status: `completed` or `failed` |
| `result.matches` | Array of matching catalog items |
| `matches[].ci_name` | Internal catalog item name (unique identifier) |
| `matches[].display_name` | Human-readable catalog item name |
| `matches[].stage` | Deployment stage: `prod`, `dev`, or `event` |
| `matches[].tier` | Relevance tier: `green` (strong match), `yellow` (partial match), `white` (weak match) |
| `matches[].rationale` | Natural language explanation of why this item matches |

#### Return Shape (timeout)

```json
{
  "status": "timeout",
  "error": "Advisor query timed out after 120s",
  "result": null
}
```

#### Return Shape (RCARS unavailable)

```json
{
  "error": "RCARS query failed after 3 retries (connection timeout to rcars-api service)",
  "status": "unavailable"
}
```

#### Example Usage

> "Check if there's existing content covering OpenShift GitOps with ArgoCD"

The tool queries RCARS with the content description and returns any existing catalog items that overlap with the proposed content. The intake skill uses this during the vetting phase to assess content uniqueness.

#### Notes

- The tool searches across all stages (`prod`, `dev`, `event`) to provide the full catalog picture during vetting
- The advisor query is asynchronous internally -- the tool submits a job, polls every 10 seconds, and returns the final result
- Timeout is 120 seconds. If the RCARS advisor takes longer, the tool returns a timeout response
- If RCARS is unreachable, the tool retries 3 times with exponential backoff (1s, 2s, 4s) before returning an unavailable response

---

### ph_rcars_catalog_search

Browse and search the RCARS catalog. Returns a paginated list of catalog items with basic metadata.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `str` | No | `""` | Search query string to filter catalog items. |
| `limit` | `int` | No | `20` | Maximum number of items to return. |

#### Return Shape

```json
{
  "items": [
    {
      "ci_name": "ocp4_getting_started",
      "display_name": "OpenShift 4 Getting Started",
      "stage": "prod",
      "category": "workshop"
    },
    {
      "ci_name": "rhel9_smart_management",
      "display_name": "RHEL 9 Smart Management",
      "stage": "prod",
      "category": "demo"
    }
  ],
  "total": 142
}
```

**Field descriptions:**

| Field | Description |
|-------|-------------|
| `items` | Array of catalog items matching the query |
| `items[].ci_name` | Internal catalog item name (unique identifier) |
| `items[].display_name` | Human-readable catalog item name |
| `items[].stage` | Deployment stage: `prod`, `dev`, or `event` |
| `items[].category` | Content category (e.g., `workshop`, `demo`) |
| `total` | Total number of items matching the query (may be greater than returned items if limited) |

#### Return Shape (RCARS unavailable)

```json
{
  "error": "RCARS catalog search failed after 3 retries (connection timeout to rcars-api service)",
  "status": "unavailable"
}
```

#### Example Usage

> "Show me RCARS catalog items about RHEL"

The tool queries the RCARS catalog and returns matching items. Useful for browsing available content before creating new projects.

---

### ph_rcars_catalog_item

Get full metadata and analysis for a specific catalog item by name.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ci_name` | `str` | Yes | The catalog item name (e.g., `ocp4_getting_started`). This is the `ci_name` value from catalog search results. |

#### Return Shape

```json
{
  "ci_name": "ocp4_getting_started",
  "display_name": "OpenShift 4 Getting Started",
  "stage": "prod",
  "category": "workshop",
  "showroom_url": "https://demo.redhat.com/...",
  "analysis": {
    "summary": "Introductory OpenShift workshop covering pods, deployments, services, routes, and basic troubleshooting.",
    "content_hash": "a1b2c3d4...",
    "staleness": "current",
    "analyzed_at": "2026-04-15T10:30:00Z"
  },
  "tags": [
    "openshift",
    "kubernetes",
    "containers",
    "getting-started"
  ]
}
```

**Field descriptions:**

| Field | Description |
|-------|-------------|
| `ci_name` | Internal catalog item name |
| `display_name` | Human-readable name |
| `stage` | Deployment stage |
| `category` | Content category |
| `showroom_url` | URL to the content on the demo platform (if available) |
| `analysis.summary` | AI-generated summary of the content |
| `analysis.content_hash` | Hash of the analyzed content version |
| `analysis.staleness` | Whether the analysis is `current` or `stale` relative to content changes |
| `analysis.analyzed_at` | Timestamp of the last analysis |
| `tags` | Array of topic tags |

#### Return Shape (item not found)

```json
{
  "error": "Catalog item 'nonexistent_item' not found",
  "status": "not_found"
}
```

#### Return Shape (RCARS unavailable)

```json
{
  "error": "RCARS catalog item lookup failed after 3 retries (connection timeout to rcars-api service)",
  "status": "unavailable"
}
```

#### Example Usage

> "Get details for the ocp4_getting_started catalog item"

The tool retrieves the full metadata including AI analysis, tags, and staleness assessment. Useful for understanding what existing content covers before deciding whether new content is needed.

---

## Project Management Tools

These tools manage Publishing House projects. They were available before the RCARS integration and continue to work alongside the new RCARS tools.

---

### ph_list_projects

List all Publishing House projects with their current phase and status. Supports filtering by owner email for Central project discovery.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `owner_email` | `str` | No | `None` | Filter projects by owner email address. If omitted, returns all projects. |

#### Return Shape

```json
[
  {
    "id": "a1b2c3d4-...",
    "name": "OpenShift GitOps Workshop",
    "repo_url": "git@github.com:rhpds/ocp-gitops-workshop.git",
    "deployment_mode": "rhdp_published",
    "phases": [
      {"phase_name": "intake", "status": "completed"},
      {"phase_name": "writing", "status": "in_progress"}
    ]
  }
]
```

#### Example Usage

> "List PH projects"

---

### ph_get_launch_instructions

Get step-by-step ordering instructions for deploying a project, derived from the manifest's deployment mode.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `str` | Yes | UUID string of the project from `ph_list_projects`. |

#### Return Shape

Returns project-specific launch instructions including deployment steps and URLs, based on `deployment_mode` (onboarded or self-published).

#### Example Usage

> "Get launch instructions for project a1b2c3d4-..."

---

### ph_store_validation_results

Store validation results from `agnosticv:validator` or `showroom:verify-content`.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str` | Yes | | UUID string of the project. |
| `phase` | `str` | Yes | | Lifecycle phase this validation applies to (e.g., `editing`, `automation`). |
| `validator` | `str` | Yes | | Name of the validator tool (e.g., `agnosticv:validator`, `showroom:verify-content`). |
| `status` | `str` | Yes | | Validation result: `passed`, `failed`, or `warning`. |
| `summary` | `str` | Yes | | Human-readable summary of findings. |
| `findings` | `list[dict]` | No | `None` | Detailed findings array. |
| `run_by` | `str` | No | `None` | Who or what ran the validation. |

#### Return Shape

```json
{
  "id": "a1b2c3d4-...",
  "project_id": "e5f6g7h8-...",
  "phase": "editing",
  "validator": "showroom:verify-content",
  "status": "passed",
  "run_at": "2026-05-04T10:00:00+00:00",
  "summary": "All checks passed"
}
```

---

### ph_get_validation_results

Get validation results for a project, optionally filtered by phase. Returns results ordered by run date (newest first).

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str` | Yes | | UUID string of the project. |
| `phase` | `str` | No | `None` | Filter results to a specific lifecycle phase. |

#### Return Shape

```json
[
  {
    "id": "a1b2c3d4-...",
    "phase": "editing",
    "validator": "showroom:verify-content",
    "status": "passed",
    "run_at": "2026-05-04T10:00:00+00:00",
    "run_by": "editor-agent",
    "summary": "All checks passed",
    "findings": []
  }
]
```

---

## Session Continuity Tools

These tools persist intake data and manifest state in Central DB, enabling session continuity across Claude Code restarts. Added in Phase 2.

---

### ph_store_intake_results

Store intake interview results in Central DB for session continuity. Creates an IntakeSession record. Used by all three deployment modes (onboarded, self_published, express).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `owner_email` | `str` | Yes | Red Hat email of the project owner. |
| `mode` | `str` | Yes | Deployment mode: `onboarded`, `self_published`, or `express`. |
| `intake_data` | `dict` | Yes | Full intake data dict (mirrors manifest project + lifecycle shape). |
| `project_name` | `str` | No | Optional project name for display. |

#### Return Shape

```json
{
  "session_id": "a1b2c3d4-...",
  "owner_email": "user@redhat.com",
  "mode": "express",
  "project_name": "My Demo",
  "status": "active",
  "created_at": "2026-05-04T10:00:00+00:00"
}
```

---

### ph_get_intake_results

Retrieve stored intake results by session ID. Returns the full intake data dict for resuming a previously started intake interview.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | `str` | Yes | UUID string of the intake session to retrieve. |

#### Return Shape

```json
{
  "session_id": "a1b2c3d4-...",
  "owner_email": "user@redhat.com",
  "mode": "onboarded",
  "project_name": "My Workshop",
  "status": "active",
  "intake_data": { ... },
  "project_id": null,
  "created_at": "2026-05-04T10:00:00+00:00",
  "updated_at": "2026-05-04T10:05:00+00:00"
}
```

#### Return Shape (not found)

```json
{
  "error": "Session a1b2c3d4-... not found"
}
```

---

### ph_list_intake_sessions

List intake sessions for a user, optionally filtered by status. Returns sessions ordered by creation date (newest first).

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `owner_email` | `str` | Yes | | Red Hat email to filter sessions by. |
| `status` | `str` | No | `None` | Filter by status: `active`, `converted`, or `abandoned`. |

#### Return Shape

```json
[
  {
    "session_id": "a1b2c3d4-...",
    "mode": "express",
    "project_name": "Quick Demo",
    "status": "active",
    "created_at": "2026-05-04T10:00:00+00:00"
  }
]
```

---

### ph_sync_manifest

Sync manifest YAML content from a skill to Central DB. Called by skills after every manifest write to keep Central in real-time sync. Sets `sync_source='mcp'` to prevent the refresh engine from overwriting MCP-pushed data.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `str` | Yes | UUID of the project whose manifest to update. |
| `manifest_yaml` | `str` | Yes | Full manifest YAML content as a string. |

#### Return Shape

```json
{
  "manifest_id": "e5f6g7h8-...",
  "project_id": "a1b2c3d4-...",
  "synced_at": "2026-05-04T10:05:00+00:00"
}
```

#### Return Shape (project not found)

```json
{
  "error": "Project a1b2c3d4-... not found"
}
```

---

### ph_record_express_run

Record a completed express mode run for aggregate metrics tracking.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `owner_email` | `str` | Yes | | Red Hat email of the user who ran express mode. |
| `base_ci` | `str` | No | `None` | RCARS catalog item used as the base environment. |
| `automated` | `bool` | No | `false` | Whether the environment ordering was fully automated. |

#### Return Shape

```json
{
  "id": "i9j0k1l2-...",
  "owner_email": "user@redhat.com",
  "base_ci": "ocp4_getting_started",
  "automated": false,
  "created_at": "2026-05-04T12:00:00+00:00"
}
```

---

## Error Handling

All RCARS tools follow the same error handling pattern:

| Scenario | Response |
|----------|----------|
| RCARS is unreachable | `{"error": "...", "status": "unavailable"}` -- after 3 retries with exponential backoff |
| RCARS returns a server error (5xx) | Retried automatically (up to 3 times). If all retries fail, returns `unavailable` |
| RCARS returns a client error (4xx) | Fails immediately (not retried). Error details in the response |
| Advisor query times out | `{"status": "timeout", "error": "...", "result": null}` -- after 120 seconds |
| Catalog item not found | `{"error": "...", "status": "not_found"}` |

Skills and Claude Code agents should handle these error responses gracefully. The intake skill offers to skip vetting when RCARS is unavailable.

## Related Documentation

- [Claude Code Setup Guide](../user/claude-code-setup.md) -- How to connect Claude Code to the MCP server
- [RCARS Integration Architecture](../architecture/rcars-integration.md) -- System design and data flow
- [MCP Auth Admin Guide](../admin/mcp-auth.md) -- API key management for admins
