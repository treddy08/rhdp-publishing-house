# MCP API Key Auth Admin Guide

## Overview

The Publishing House MCP endpoint (`/mcp`) uses API key authentication for external Claude Code users. Keys are SHA-256 hashed and stored in a Kubernetes Secret that is volume-mounted into the backend pod. The FastMCP `ApiKeyAuth` Middleware validates every tool call before dispatch.

This guide covers the full API key lifecycle: generation, distribution, revocation, and troubleshooting.

## Key Generation

Follow these steps to create a new API key for a user.

### Step 1: Generate the raw key

```bash
openssl rand -hex 32
```

This produces a 64-character hex string (256 bits of entropy). Save this value -- you will give it to the user in Step 5.

### Step 2: Hash the key

```bash
echo -n "<raw-key>" | sha256sum | awk '{print $1}'
```

Replace `<raw-key>` with the actual key from Step 1. This produces the SHA-256 hash that gets stored in the Secret.

### Step 3: Add the hash to Ansible vars

Edit `ansible/vars/dev.yml` (or `ansible/vars/prod.yml` for production) in the `rhdp-publishing-house-portal` repo. Add the hashed value to the `mcp_api_keys` dictionary:

```yaml
mcp_api_keys:
  nate: "<sha256-hash-from-step-2>"
  prakhar: "<sha256-hash>"
```

The key name (e.g., `nate`) is an admin identifier for bookkeeping -- it tells you who has this key. It is not used for authentication.

**Never commit `dev.yml` or `prod.yml` to git.** These files are gitignored. Only `.example` files are tracked.

### Step 4: Deploy

Run the Ansible deployer to update the Secret and restart the backend pod:

```bash
cd rhdp-publishing-house-portal && ansible-playbook ansible/deploy.yml -e env=dev --tags apply
```

The `apply` tag updates manifests (Secrets, ConfigMaps, Deployments) without triggering a rebuild. The backend pod restarts to pick up the new key file (D-01: no hot-reload in Phase 1). Only use `--tags deploy` if you also need to rebuild code and run migrations.

### Step 5: Distribute the raw key

Give the **raw key** (from Step 1) to the user. They will add it to their Claude Code MCP configuration. See the [Claude Code Setup Guide](../user/claude-code-setup.md) for user-facing instructions.

**Never share the SHA-256 hash.** The hash is the stored credential; the raw key is the user credential.

## Key Revocation

To revoke a user's API key:

1. Remove the user's entry from `mcp_api_keys` in `ansible/vars/dev.yml`
2. Apply the change:
   ```bash
   cd rhdp-publishing-house-portal && ansible-playbook ansible/deploy.yml -e env=dev --tags apply
   ```
3. The backend pod restarts and loads the updated key file. The revoked key is immediately invalid.

## Key Rotation

To rotate a key (e.g., if a key may have been compromised):

1. Generate a new key (Steps 1-2 above)
2. Replace the old hash with the new hash in `ansible/vars/dev.yml`
3. Redeploy (Step 4)
4. Give the new raw key to the user (Step 5)

The old key becomes invalid as soon as the pod restarts with the updated Secret.

## Key Storage

API keys are stored in a Kubernetes Secret named `ph-mcp-api-keys` in the `publishing-house-dev` namespace. The Secret is volume-mounted into the backend pod at `/etc/ph/mcp-api-keys/keys.yaml`.

### File format

```yaml
user-name: "sha256:<hex-digest>"
another-user: "sha256:<hex-digest>"
```

Each entry maps an admin-chosen key name to a `sha256:`-prefixed hex digest. The backend strips the `sha256:` prefix when loading keys and compares against the hash of the incoming raw key.

### How validation works

1. Claude Code sends `Authorization: Bearer <raw-key>` in the MCP request
2. The `ApiKeyAuth` Middleware extracts the raw key from the header
3. The middleware computes `hashlib.sha256(raw_key.encode()).hexdigest()`
4. The middleware compares the computed hash against each stored hash using `hmac.compare_digest()` (timing-safe)
5. If any stored hash matches, the tool call proceeds. If none match, a `ToolError` is raised

## Ansible Integration

The API key Secret is defined in the portal's Ansible infrastructure template (`ansible/templates/manifests-infra.yaml.j2`). The template iterates over the `mcp_api_keys` dictionary from vars and generates the Secret content using `dict2items`:

```yaml
stringData:
  keys.yaml: |
{% for key in mcp_api_keys | default({}) | dict2items %}
    {{ key.key }}: "sha256:{{ key.value }}"
{% endfor %}
```

The `mcp_api_keys` variable lives in env-specific vars files (`vars/dev.yml`, `vars/prod.yml`) which are gitignored.

## Troubleshooting

### "Authentication required: missing or invalid Authorization header"

**Cause:** The request does not have an `Authorization` header or it does not start with `Bearer `.

**Fix:** Verify the Claude Code MCP config includes the `headers` block with `Authorization: Bearer <key>`. See the [Claude Code Setup Guide](../user/claude-code-setup.md).

### "Authentication failed: invalid API key"

**Cause:** The raw key does not match any stored hash.

**Possible reasons:**
- The key was revoked (removed from vars and redeployed)
- The key was rotated (replaced with a new key)
- The key was entered incorrectly in the user's MCP config (whitespace, truncation)
- The key hash was generated incorrectly (e.g., missing `-n` flag on `echo`)

**Fix:** Verify the raw key matches the expected hash:
```bash
echo -n "<raw-key>" | sha256sum | awk '{print $1}'
```
Compare the output with the value stored in `ansible/vars/dev.yml`.

### "No valid keys loaded" or empty key file

**Cause:** The key file was not found at the expected mount path, or the file is empty.

**Possible reasons:**
- The Secret does not exist in the namespace
- The volume mount path does not match the configured key file path
- The `mcp_api_keys` dictionary is empty in the Ansible vars

**Fix:**
1. Verify the Secret exists:
   ```bash
   oc get secret ph-mcp-api-keys -n publishing-house-dev
   ```
2. Verify the file exists inside the pod:
   ```bash
   oc exec deployment/ph-portal-backend -n publishing-house-dev -- cat /etc/ph/mcp-api-keys/keys.yaml
   ```
3. Verify `mcp_api_keys` is not empty in `ansible/vars/dev.yml`

### Key change not taking effect

**Cause:** The backend pod has not restarted after a key change.

**Fix:** The backend reads the key file at startup only (D-01). After updating keys and redeploying, verify the pod restarted:
```bash
oc get pods -l app=ph-portal,component=backend -n publishing-house-dev
```
The pod age should be recent (seconds/minutes, not hours/days).

## Related Documentation

- [RCARS Integration Architecture](../architecture/rcars-integration.md)
- [Claude Code Setup Guide](../user/claude-code-setup.md)
- [Portal Deployment](portal-deployment.md)
