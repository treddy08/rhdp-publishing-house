# Claude Code Setup Guide

## Overview

Publishing House exposes MCP tools that let Claude Code query the RCARS content advisory system, persist intake data across sessions, sync manifest state to the portal, and track express mode usage. This guide explains how to connect Claude Code to the Publishing House MCP server.

## Prerequisites

- **Claude Code** installed ([installation guide](https://docs.anthropic.com/en/docs/claude-code))
- **Publishing House skills plugin** installed (see [Getting Started](../getting-started.md))
- **API key** received from a PH admin (ask your team lead or PH administrator)

## MCP Server Configuration

### Option 1: Global settings (recommended)

Add the PH MCP server to your Claude Code global settings so it's available in every session. Open `~/.claude/settings.json` and add the `mcpServers` block:

```json
{
  "mcpServers": {
    "publishing-house": {
      "type": "http",
      "url": "https://ph-mcp.apps.<cluster-domain>/mcp/",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

Replace:
- `<cluster-domain>` with the OpenShift cluster apps domain (ask your admin for the exact URL)
- `<your-api-key>` with the raw API key provided by your admin

Restart Claude Code after saving. The PH MCP tools will be available in every session automatically.

### Option 2: Per-session config file

If you prefer to keep the MCP config separate, create a JSON file (store it somewhere secure — it contains your API key):

```json
{
  "mcpServers": {
    "publishing-house": {
      "type": "http",
      "url": "https://ph-mcp.apps.<cluster-domain>/mcp/",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

Then launch Claude Code with the config flag:

```bash
claude --mcp-config /path/to/your/ph-mcp.json
```

This approach requires passing the flag every session but keeps the API key out of your global settings.

## Verify Connection

After configuring the MCP server:

1. Start or restart Claude Code
2. Claude Code should show `publishing-house` as an available MCP server
3. Test by asking Claude: "List PH projects" (this invokes the `ph_list_projects` tool)
4. If the connection is working, you will see a list of projects (or an empty list if none exist yet)

## Available Tools

Once connected, Claude Code can use the following MCP tools:

### RCARS Content Advisory Tools

| Tool | Description |
|------|-------------|
| `ph_rcars_query` | Submit a content vetting query to the RCARS advisor. Returns matching catalog items with relevance tiers and rationale. Used during intake vetting. |
| `ph_rcars_catalog_search` | Browse and search the RCARS catalog. Returns a paginated list of catalog items with basic metadata. |
| `ph_rcars_catalog_item` | Get full metadata and analysis for a specific catalog item by name. |

### Project Management Tools

| Tool | Description |
|------|-------------|
| `ph_list_projects` | List all Publishing House projects with their current phase and status. Supports `owner_email` filter. |
| `ph_get_launch_instructions` | Get step-by-step ordering instructions for deploying a project. |
| `ph_store_validation_results` | Store validation results from `agnosticv:validator` or `showroom:verify-content`. |
| `ph_get_validation_results` | Retrieve stored validation results for a project, optionally filtered by phase. |

### Session Continuity Tools

| Tool | Description |
|------|-------------|
| `ph_store_intake_results` | Persist intake interview data in the portal DB. Used by all three modes (onboarded, self-published, express). |
| `ph_get_intake_results` | Retrieve previously stored intake data by session ID. Enables resuming intake across Claude Code restarts. |
| `ph_list_intake_sessions` | List intake sessions for a user, optionally filtered by status. |
| `ph_sync_manifest` | Sync manifest YAML to the portal DB after every manifest write. Keeps the portal in real-time sync. |
| `ph_record_express_run` | Record a completed express mode run for aggregate metrics tracking. |

For detailed parameter and return shape documentation, see the [MCP Tools Reference](../api/mcp-tools.md).

## Usage Examples

### Content vetting during intake

When creating a new project, the intake skill automatically uses `ph_rcars_query` to check for existing content overlap. You can also invoke it directly:

> "Check if there's existing RHDP content covering OpenShift GitOps with ArgoCD"

Claude will call `ph_rcars_query` and present matching catalog items with relevance assessments.

### Browsing the catalog

> "Show me what RCARS catalog items exist for RHEL"

Claude will call `ph_rcars_catalog_search` and list matching items.

### Looking up a specific item

> "Get details for the ocp4_getting_started catalog item from RCARS"

Claude will call `ph_rcars_catalog_item` and return the full metadata including analysis, tags, and content assessment.

## Troubleshooting

### "Connection refused" or "Failed to connect"

**Cause:** The MCP server URL is incorrect or the server is not running.

**Fix:**
1. Verify the URL in your MCP config matches the format `https://ph-mcp.apps.<cluster-domain>/mcp`
2. Check with your admin that the PH backend is deployed and the MCP route is active
3. Ensure you are on a network that can reach the OpenShift cluster (VPN may be required)

### "Authentication required" (401)

**Cause:** The API key is missing or malformed in your MCP config.

**Fix:**
1. Verify the `headers` block exists in your MCP config with `"Authorization": "Bearer <your-api-key>"`
2. Ensure there are no extra spaces or newlines in the API key value
3. Confirm the `type` field is set to `"http"` (not `"sse"` or `"stdio"`)

### "Authentication failed" (invalid key)

**Cause:** Your API key has been revoked or rotated.

**Fix:** Contact your PH admin for a new API key.

### Tool not found

**Cause:** The MCP server may not be connected, or there is a configuration issue.

**Fix:**
1. Restart Claude Code
2. Check that `publishing-house` appears in the list of available MCP servers
3. If not listed, verify your MCP config file is valid JSON and in the correct location

### "RCARS unavailable" in tool response

**Cause:** The RCARS service is temporarily down or unreachable from the PH backend.

**Fix:** This is not a client-side issue. The PH backend retries automatically with exponential backoff. If the error persists, contact the platform team. The intake skill can proceed without vetting -- it will offer to skip the RCARS check.

## Related Documentation

- [Getting Started](../getting-started.md) -- Full PH setup including skills plugin
- [MCP Tools Reference](../api/mcp-tools.md) -- Detailed tool documentation
- [RCARS Integration Architecture](../architecture/rcars-integration.md) -- How the integration works
