# MCP Tools Reference

This document describes all MCP tools available on the Publishing House MCP server. Tools are organized by category: RCARS content advisory tools (new in Phase 1) and project management tools (existing).

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
      },
      {
        "ci_name": "ocp4_advanced_networking",
        "display_name": "OpenShift 4 Advanced Networking",
        "stage": "dev",
        "tier": "yellow",
        "rationale": "Partial overlap in networking topics but focuses on SDN/OVN deep dive."
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
- The advisor query is asynchronous internally -- the tool submits a job, polls every 3 seconds, and returns the final result
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

List all Publishing House projects with their current phase and status.

#### Parameters

None.

#### Return Shape

```json
{
  "projects": [
    {
      "id": 1,
      "name": "OpenShift GitOps Workshop",
      "status": "active",
      "current_phase": "writing",
      "deployment_mode": "rhdp_published"
    }
  ]
}
```

#### Example Usage

> "List PH projects"

---

### ph_get_launch_instructions

Get launch instructions for a specific project.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `int` | Yes | The project ID from `ph_list_projects`. |

#### Return Shape

Returns project-specific launch instructions including deployment steps and URLs.

#### Example Usage

> "Get launch instructions for project 1"

---

### ph_store_validation_results

Store validation results for a project's content.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `int` | Yes | The project ID. |
| `results` | `dict` | Yes | Validation results object. |

#### Return Shape

```json
{
  "stored": true,
  "project_id": 1
}
```

---

### ph_get_validation_results

Retrieve stored validation results for a project.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `int` | Yes | The project ID. |

#### Return Shape

Returns the previously stored validation results dict, or an error if none exist.

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
