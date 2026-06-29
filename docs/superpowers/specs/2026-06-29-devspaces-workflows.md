# Dev Spaces Integration — Workflow Documentation

**Date:** 2026-06-29
**Parent Spec:** [2026-06-29-devspaces-implementation.md](./2026-06-29-devspaces-implementation.md)
**Purpose:** Step-by-step workflows for all Dev Spaces workspace lifecycle operations

---

## Table of Contents

1. [Create Workspace (First Time)](#1-create-workspace-first-time)
2. [Resume Workspace (Stopped, Valid Key)](#2-resume-workspace-stopped-valid-key)
3. [Resume Workspace (Stopped, Expired Key - Auto-Rotation)](#3-resume-workspace-stopped-expired-key---auto-rotation)
4. [Delete Workspace](#4-delete-workspace)
5. [Get Key History (Audit)](#5-get-key-history-audit)
6. [Error Scenarios](#6-error-scenarios)

---

## 1. Create Workspace (First Time)

**User Action:** Clicks "Launch Workspace" button on project detail page

**Preconditions:**
- User is authenticated via OAuth
- Project exists in database
- No workspace exists for this project+user combination
- LiteLLM endpoint is accessible
- Dev Spaces operator is running on cluster

### Flow Diagram

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Browser │────▶│ Portal   │────▶│ LiteLLM  │     │ K8s API  │     │ Database │
│         │     │ Backend  │     │          │     │          │     │          │
└─────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                 │                │                │
     │  POST /workspace                │                │                │
     ├───────────────▶│                 │                │                │
     │                │                 │                │                │
     │                │  Check existing workspace                        │
     │                ├─────────────────────────────────────────────────▶│
     │                │◀─────────────────────────────────────────────────┤
     │                │  None found                                      │
     │                │                 │                │                │
     │                │  POST /key/generate              │                │
     │                ├────────────────▶│                │                │
     │                │◀────────────────┤                │                │
     │                │  {key, key_id}  │                │                │
     │                │                 │                │                │
     │                │  Create namespace                │                │
     │                ├──────────────────────────────────▶│                │
     │                │◀──────────────────────────────────┤                │
     │                │  Namespace created                │                │
     │                │                 │                │                │
     │                │  Create DevWorkspace CR          │                │
     │                │  (with MAAS_API_KEY env var)     │                │
     │                ├──────────────────────────────────▶│                │
     │                │◀──────────────────────────────────┤                │
     │                │  {workspace_id, status}           │                │
     │                │                 │                │                │
     │                │  INSERT workspaces                                │
     │                ├─────────────────────────────────────────────────▶│
     │                │  INSERT workspace_key_history                    │
     │                ├─────────────────────────────────────────────────▶│
     │                │◀─────────────────────────────────────────────────┤
     │                │  Committed                                        │
     │                │                 │                │                │
     │  {url, status} │                 │                │                │
     │◀───────────────┤                 │                │                │
     │                │                 │                │                │
     │  Redirect to workspace_url                        │                │
     ├───────────────────────────────────────────────────┘                │
     │                                                                     │
     ▼                                                                     │
VS Code in browser opens                                                  │
Workspace startup script runs                                             │
Claude Code configured automatically                                      │
```

### Step-by-Step Execution

#### Step 1: User clicks "Launch Workspace"

**Browser:**
```javascript
POST /api/v1/projects/{project_id}/workspace
Headers:
  Authorization: Bearer {oauth_token}
```

#### Step 2: Portal backend receives request

**Backend (app/api/workspaces.py):**
```python
@router.post("")
async def create_workspace(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    manager: WorkspaceManager = Depends(get_workspace_manager)
)
```

**Extracts:**
- `user_id`: "treddy" (from OAuth token)
- `user_email`: "treddy@redhat.com" (from OAuth token)
- `project_id`: UUID from URL path

#### Step 3: Check for existing workspace

**Database Query:**
```sql
SELECT * FROM workspaces 
WHERE project_id = {uuid} AND user_id = 'treddy';
```

**Result:** No rows (workspace doesn't exist yet)

#### Step 4: Provision MaaS key via LiteLLM

**HTTP Request:**
```http
POST https://litellm.example.com/key/generate
Authorization: Bearer {litellm_master_key}
Content-Type: application/json

{
  "key_alias": "ph-treddy-abc123ef",
  "duration": "30d",
  "models": ["claude-sonnet-4-5"],
  "metadata": {
    "owner": "treddy@redhat.com",
    "project_id": "abc123ef-...",
    "created_by": "publishing-house"
  },
  "max_budget": null
}
```

**Response:**
```json
{
  "key": "sk-ant-api03-abcd1234...",
  "key_id": "key_f8g9h0i1j2k3",
  "expires": "2026-07-29T12:00:00Z"
}
```

**State Change:**
- LiteLLM: Key created, status=active
- Can authenticate API calls immediately

#### Step 5: Create Kubernetes namespace

**K8s API Call:**
```python
core_api.create_namespace(
    body=V1Namespace(
        metadata=V1ObjectMeta(name="devworkspace-treddy")
    )
)
```

**Result:**
- Namespace `devworkspace-treddy` created
- Default ServiceAccount created automatically

#### Step 6: Create DevWorkspace CR

**K8s Custom Resource:**
```yaml
apiVersion: workspace.devfile.io/v1alpha2
kind: DevWorkspace
metadata:
  name: ph-abc123ef
  namespace: devworkspace-treddy
  labels:
    app.kubernetes.io/managed-by: publishing-house
spec:
  routingClass: che
  started: true
  contributions:
  - name: ide
    uri: http://devspaces-dashboard.openshift-devspaces.svc:8080/dashboard/api/editors/devfile?che-editor=che-incubator/che-code/latest
  template:
    projects:
    - name: project
      git:
        remotes:
          origin: https://github.com/user/project.git
        checkoutFrom:
          revision: main
    components:
    - name: dev
      container:
        image: quay.io/rhpds/ph-udi:latest
        memoryLimit: 4Gi
        cpuLimit: "2"
        env:
        - name: MAAS_API_KEY
          value: "sk-ant-api03-abcd1234..."  # ← Injected here
        - name: MCP_ENDPOINT
          value: "https://publishing-house-central-dev.apps.../mcp"
        - name: LITELLM_URL
          value: "https://litellm.example.com"
        - name: PROJECT_ID
          value: "abc123ef-..."
        - name: PROJECT_REPO_NAME
          value: "project"
    commands:
    - id: post-start
      exec:
        component: dev
        commandLine: /opt/ph/scripts/workspace-startup.sh
        workingDir: /projects
    events:
      postStart:
      - post-start
```

**Result:**
- DevWorkspace CR created
- Dev Spaces operator starts reconciliation
- Pod created: `ph-abc123ef-xxxxx` in namespace `devworkspace-treddy`
- Route created: `https://ph-abc123ef-devworkspace-treddy.apps.ocpv-infra01.../`

#### Step 7: Store workspace in database

**Database Transaction:**
```sql
BEGIN;

-- Create workspace record
INSERT INTO workspaces (
  id, project_id, user_id, user_email,
  workspace_id, workspace_namespace, workspace_name, workspace_url,
  maas_key_id, maas_key_alias,
  created_at, updated_at
) VALUES (
  'ws-uuid-...',
  'abc123ef-...',
  'treddy',
  'treddy@redhat.com',
  'k8s-workspace-uid',
  'devworkspace-treddy',
  'ph-abc123ef',
  'https://ph-abc123ef-devworkspace-treddy.apps.ocpv-infra01.../',
  'key_f8g9h0i1j2k3',
  'ph-treddy-abc123ef',
  NOW(),
  NOW()
);

-- Record key in history
INSERT INTO workspace_key_history (
  id, workspace_id,
  maas_key_id, maas_key_alias,
  provisioned_at, duration, models, is_current
) VALUES (
  'hist-uuid-...',
  'ws-uuid-...',
  'key_f8g9h0i1j2k3',
  'ph-treddy-abc123ef',
  NOW(),
  '30d',
  '["claude-sonnet-4-5"]',
  true
);

COMMIT;
```

**State Change:**
- Database: Workspace recorded
- Key history: Initial key recorded as current

#### Step 8: Return workspace URL to browser

**HTTP Response:**
```json
{
  "url": "https://ph-abc123ef-devworkspace-treddy.apps.ocpv-infra01.../",
  "status": "starting"
}
```

#### Step 9: Browser redirects to workspace

**Browser Action:**
```javascript
window.location.href = response.url;
```

**User lands in:** VS Code in browser (Dev Spaces workspace)

#### Step 10: Workspace startup script executes

**Auto-executed on workspace start:**
```bash
#!/bin/bash
# /opt/ph/scripts/workspace-startup.sh

# Update Claude Code CLI
npm update -g @anthropic-ai/claude-code

# Update PH skills
cd /opt/ph/skills && git pull --rebase --autostash

# Sync project repo
cd /projects/project
git pull --rebase --autostash

# Validate MaaS key
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${MAAS_API_KEY}" \
  "${LITELLM_URL}/health"

# Configure Claude Code
export ANTHROPIC_API_KEY="${MAAS_API_KEY}"
export ANTHROPIC_BASE_URL="${LITELLM_URL}/v1"

# Link PH skills
mkdir -p ~/.config/claude-code/skills
ln -sf /opt/ph/skills ~/.config/claude-code/skills/publishing-house
```

**Result:**
- Claude Code updated to latest version
- PH skills available
- Project repo cloned and synced
- Environment configured
- User ready to use Claude Code

### Final State

| System | State |
|--------|-------|
| **LiteLLM** | Key `key_f8g9h0i1j2k3` active, expires in 30 days |
| **K8s** | Namespace + DevWorkspace created, pod running |
| **Database** | Workspace + key_history records inserted |
| **Browser** | VS Code open, Claude Code ready |

### Duration

**End-to-end:** ~45-60 seconds
- LiteLLM key provision: ~500ms
- K8s namespace + CR creation: ~2s
- Database inserts: ~50ms
- Pod startup: ~30-45s (image pull + container start)
- Workspace UI ready: ~5-10s

---

## 2. Resume Workspace (Stopped, Valid Key)

**User Action:** Clicks "Open Workspace" button (workspace exists, is stopped, key still valid)

**Preconditions:**
- Workspace record exists in database
- DevWorkspace CR exists in K8s (but `started: false`)
- MaaS key is still valid (not expired)

### Flow Diagram

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Browser │────▶│ Portal   │────▶│ K8s API  │     │ Database │
│         │     │ Backend  │     │          │     │          │
└─────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │
     │  GET /workspace                 │                │
     ├───────────────▶│                │                │
     │                │                │                │
     │                │  SELECT workspace              │
     │                ├────────────────────────────────▶│
     │                │◀────────────────────────────────┤
     │                │  {workspace record}             │
     │                │                │                │
     │  {url, status} │                │                │
     │◀───────────────┤                │                │
     │                │                │                │
     │  Redirect to URL                │                │
     ├─────────────────────────────────┘                │
```

### Step-by-Step Execution

#### Step 1: User clicks "Open Workspace"

**Browser:**
```javascript
GET /api/v1/projects/{project_id}/workspace
```

#### Step 2: Backend retrieves workspace from database

**Database Query:**
```sql
SELECT * FROM workspaces 
WHERE project_id = {uuid} AND user_id = 'treddy';
```

**Result:**
```json
{
  "id": "ws-uuid-...",
  "workspace_url": "https://ph-abc123ef-devworkspace-treddy.apps.../",
  "maas_key_id": "key_f8g9h0i1j2k3",
  ...
}
```

#### Step 3: Optional - Check K8s status

**K8s API Call:**
```python
ws = custom_api.get_namespaced_custom_object(
    group="workspace.devfile.io",
    version="v1alpha2",
    namespace="devworkspace-treddy",
    plural="devworkspaces",
    name="ph-abc123ef"
)
status = ws["status"]["phase"]  # "Stopped"
```

#### Step 4: Return workspace URL

**HTTP Response:**
```json
{
  "url": "https://ph-abc123ef-devworkspace-treddy.apps.../",
  "status": "stopped"
}
```

#### Step 5: Browser redirects

**Browser Action:**
```javascript
window.location.href = response.url;
```

**Dev Spaces detects access:**
- User accesses workspace URL
- Dev Spaces automatically starts the workspace
- Pod transitions from Stopped → Starting → Running
- Startup script executes
- User lands in VS Code

### Duration

**End-to-end:** ~10-20 seconds
- Database query: ~10ms
- Redirect: instant
- Pod startup (from stopped): ~5-15s (container already cached)

---

## 3. Resume Workspace (Stopped, Expired Key - Auto-Rotation)

**User Action:** Clicks "Resume Workspace" button after key has expired

**Preconditions:**
- Workspace exists, DevWorkspace CR exists
- MaaS key has expired (>30 days old)
- LiteLLM rejects API calls with expired key

### Flow Diagram

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Browser │────▶│ Portal   │────▶│ LiteLLM  │     │ K8s API  │     │ Database │
│         │     │ Backend  │     │          │     │          │     │          │
└─────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │                │
     │  POST /workspace/start          │                │                │
     ├───────────────▶│                │                │                │
     │                │                │                │                │
     │                │  SELECT workspace              │                │
     │                ├────────────────────────────────────────────────▶│
     │                │◀────────────────────────────────────────────────┤
     │                │                │                │                │
     │                │  GET /key/info │                │                │
     │                ├────────────────▶│                │                │
     │                │◀────────────────┤                │                │
     │                │  404 Not Found  │                │                │
     │                │  (Key expired)  │                │                │
     │                │                │                │                │
     │                │  UPDATE old key: expired_at=NOW()               │
     │                ├─────────────────────────────────────────────────▶│
     │                │                │                │                │
     │                │  POST /key/generate (new key)  │                │
     │                ├────────────────▶│                │                │
     │                │◀────────────────┤                │                │
     │                │  {new_key}      │                │                │
     │                │                │                │                │
     │                │  UPDATE workspace.maas_key_id                   │
     │                ├─────────────────────────────────────────────────▶│
     │                │  INSERT new key_history record                  │
     │                ├─────────────────────────────────────────────────▶│
     │                │                │                │                │
     │                │  POST /key/delete (old key)    │                │
     │                ├────────────────▶│                │                │
     │                │◀────────────────┤                │                │
     │                │  OK             │                │                │
     │                │                │                │                │
     │                │  UPDATE old key: revoked_at=NOW()              │
     │                ├─────────────────────────────────────────────────▶│
     │                │                │                │                │
     │                │  PATCH DevWorkspace              │                │
     │                │  (update MAAS_API_KEY env)       │                │
     │                ├──────────────────────────────────▶│                │
     │                │◀──────────────────────────────────┤                │
     │                │                │                │                │
     │                │  PATCH DevWorkspace: started=true │               │
     │                ├──────────────────────────────────▶│                │
     │                │◀──────────────────────────────────┤                │
     │                │                │                │                │
     │  {url, status} │                │                │                │
     │◀───────────────┤                │                │                │
     │                │                │                │                │
     │  Redirect to workspace          │                │                │
     └────────────────────────────────────────────────────┘                │
```

### Step-by-Step Execution

#### Step 1: User clicks "Resume Workspace"

**Browser:**
```javascript
POST /api/v1/projects/{project_id}/workspace/start
```

#### Step 2: Backend retrieves workspace

**Database Query:**
```sql
SELECT * FROM workspaces 
WHERE project_id = {uuid} AND user_id = 'treddy';
```

#### Step 3: Validate current key

**HTTP Request to LiteLLM:**
```http
GET https://litellm.example.com/key/info?key_id=key_f8g9h0i1j2k3
Authorization: Bearer {litellm_master_key}
```

**Response:**
```http
404 Not Found
```

**Interpretation:** Key has expired (reached 30-day TTL)

#### Step 4: Mark old key as expired in database

**Database Update:**
```sql
UPDATE workspace_key_history
SET 
  is_current = false,
  expired_at = NOW(),
  revocation_reason = 'expired'
WHERE workspace_id = 'ws-uuid-...' AND is_current = true;
```

**State Change:**
- Old key marked as no longer current
- `expired_at` timestamp recorded
- Reason: natural expiration

#### Step 5: Provision new MaaS key

**HTTP Request to LiteLLM:**
```http
POST https://litellm.example.com/key/generate
{
  "key_alias": "ph-treddy-abc123ef",  # Same alias
  "duration": "30d",
  "models": ["claude-sonnet-4-5"],
  "metadata": {
    "owner": "treddy@redhat.com",
    "project_id": "abc123ef-...",
    "created_by": "publishing-house"
  },
  "max_budget": null
}
```

**Response:**
```json
{
  "key": "sk-ant-api03-xyz789...",  # New key
  "key_id": "key_m4n5o6p7q8r9",      # New key_id
  "expires": "2026-07-29T..."
}
```

**State Change:**
- LiteLLM: New key created, active
- Old key still exists in LiteLLM (expired, not yet deleted)

#### Step 6: Update workspace with new key

**Database Transaction:**
```sql
BEGIN;

-- Update workspace to point to new key
UPDATE workspaces
SET 
  maas_key_id = 'key_m4n5o6p7q8r9',
  updated_at = NOW()
WHERE id = 'ws-uuid-...';

-- Record new key in history
INSERT INTO workspace_key_history (
  id, workspace_id,
  maas_key_id, maas_key_alias,
  provisioned_at, duration, models, is_current
) VALUES (
  'hist-uuid-new-...',
  'ws-uuid-...',
  'key_m4n5o6p7q8r9',
  'ph-treddy-abc123ef',
  NOW(),
  '30d',
  '["claude-sonnet-4-5"]',
  true
);

COMMIT;
```

**State Change:**
- Database: Workspace points to new key
- Key history: Two records now (old + new)

#### Step 7: Revoke old key from LiteLLM

**HTTP Request:**
```http
POST https://litellm.example.com/key/delete
{
  "keys": ["key_f8g9h0i1j2k3"]  # Old key
}
```

**Response:**
```http
200 OK
```

**State Change:**
- LiteLLM: Old key permanently deleted
- Old key can no longer authenticate (already expired, now deleted)

#### Step 8: Record revocation timestamp

**Database Update:**
```sql
UPDATE workspace_key_history
SET revoked_at = NOW()
WHERE maas_key_id = 'key_f8g9h0i1j2k3';
```

**Final state of old key record:**
```json
{
  "maas_key_id": "key_f8g9h0i1j2k3",
  "is_current": false,
  "provisioned_at": "2026-05-30T12:00:00Z",
  "expired_at": "2026-06-29T12:00:00Z",      # Natural expiration
  "revoked_at": "2026-06-29T12:05:00Z",      # Manual revocation
  "revocation_reason": "expired"
}
```

#### Step 9: Update DevWorkspace env vars

**K8s API Call:**
```python
# Get current DevWorkspace
ws = custom_api.get_namespaced_custom_object(
    group="workspace.devfile.io",
    version="v1alpha2",
    namespace="devworkspace-treddy",
    plural="devworkspaces",
    name="ph-abc123ef"
)

# Update MAAS_API_KEY in dev container env
for component in ws["spec"]["template"]["components"]:
    if component["name"] == "dev":
        for env_var in component["container"]["env"]:
            if env_var["name"] == "MAAS_API_KEY":
                env_var["value"] = "sk-ant-api03-xyz789..."  # New key

# Patch the DevWorkspace
custom_api.patch_namespaced_custom_object(
    group="workspace.devfile.io",
    version="v1alpha2",
    namespace="devworkspace-treddy",
    plural="devworkspaces",
    name="ph-abc123ef",
    body=ws
)
```

**State Change:**
- DevWorkspace CR updated
- New key will be injected on next pod start

#### Step 10: Start workspace

**K8s API Call:**
```python
# Patch DevWorkspace to start
custom_api.patch_namespaced_custom_object(
    group="workspace.devfile.io",
    version="v1alpha2",
    namespace="devworkspace-treddy",
    plural="devworkspaces",
    name="ph-abc123ef",
    body={"spec": {"started": True}}
)
```

**Result:**
- Dev Spaces operator reconciles
- Pod starts with new MAAS_API_KEY env var
- Startup script runs
- Claude Code configured with new key

#### Step 11: Return workspace URL

**HTTP Response:**
```json
{
  "url": "https://ph-abc123ef-devworkspace-treddy.apps.../",
  "status": "starting"
}
```

#### Step 12: Browser redirects

**User lands in:** VS Code with new MaaS key active

### Duration

**End-to-end:** ~15-25 seconds
- Key validation (404): ~200ms
- New key provision: ~500ms
- Database updates: ~100ms
- Old key revocation: ~500ms
- K8s patch operations: ~1-2s
- Pod startup: ~10-15s

### Audit Trail Result

**Database now contains:**

```sql
SELECT * FROM workspace_key_history 
WHERE workspace_id = 'ws-uuid-...' 
ORDER BY provisioned_at DESC;
```

| maas_key_id | is_current | provisioned_at | expired_at | revoked_at | revocation_reason |
|-------------|------------|----------------|------------|------------|-------------------|
| key_m4n5o6p7q8r9 | true | 2026-06-29 12:05 | NULL | NULL | NULL |
| key_f8g9h0i1j2k3 | false | 2026-05-30 12:00 | 2026-06-29 12:05 | 2026-06-29 12:05 | expired |

**Interpretation:**
- Original key: Provisioned 30 days ago, expired today, revoked today
- New key: Provisioned today, currently active

---

## 4. Delete Workspace

**User Action:** Clicks "Delete Workspace" button

**Preconditions:**
- Workspace exists in database
- DevWorkspace CR exists in K8s
- MaaS key exists (either active or expired)

### Flow Diagram

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Browser │────▶│ Portal   │────▶│ LiteLLM  │     │ K8s API  │     │ Database │
│         │     │ Backend  │     │          │     │          │     │          │
└─────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │                │
     │  DELETE /workspace              │                │                │
     ├───────────────▶│                │                │                │
     │                │                │                │                │
     │                │  SELECT workspace + current key                │
     │                ├─────────────────────────────────────────────────▶│
     │                │◀─────────────────────────────────────────────────┤
     │                │                │                │                │
     │                │  UPDATE key: revoked_at=NOW(), reason='workspace_deleted' │
     │                ├─────────────────────────────────────────────────▶│
     │                │                │                │                │
     │                │  DELETE DevWorkspace CR         │                │
     │                ├──────────────────────────────────▶│                │
     │                │◀──────────────────────────────────┤                │
     │                │                │                │                │
     │                │  DELETE Namespace               │                │
     │                ├──────────────────────────────────▶│                │
     │                │◀──────────────────────────────────┤                │
     │                │                │                │                │
     │                │  POST /key/delete                │                │
     │                ├────────────────▶│                │                │
     │                │◀────────────────┤                │                │
     │                │  OK (key deleted)                │                │
     │                │                │                │                │
     │                │  COMMIT (preserves key_history)                 │
     │                ├─────────────────────────────────────────────────▶│
     │                │                │                │                │
     │                │  DELETE workspace record        │                │
     │                ├─────────────────────────────────────────────────▶│
     │                │◀─────────────────────────────────────────────────┤
     │                │                │                │                │
     │  204 No Content│                │                │                │
     │◀───────────────┤                │                │                │
```

### Step-by-Step Execution

#### Step 1: User clicks "Delete Workspace"

**Browser:**
```javascript
DELETE /api/v1/projects/{project_id}/workspace
```

**User sees:** Confirmation dialog (optional, frontend)

#### Step 2: Backend retrieves workspace

**Database Query:**
```sql
SELECT w.*, h.maas_key_id, h.is_current
FROM workspaces w
LEFT JOIN workspace_key_history h ON h.workspace_id = w.id AND h.is_current = true
WHERE w.project_id = {uuid} AND w.user_id = 'treddy';
```

**Result:**
```json
{
  "workspace": {
    "id": "ws-uuid-...",
    "workspace_namespace": "devworkspace-treddy",
    "workspace_name": "ph-abc123ef",
    "maas_key_id": "key_m4n5o6p7q8r9"
  },
  "current_key": {
    "maas_key_id": "key_m4n5o6p7q8r9",
    "is_current": true
  }
}
```

#### Step 3: Mark current key as revoked (BEFORE deletion)

**Database Update:**
```sql
UPDATE workspace_key_history
SET 
  is_current = false,
  revoked_at = NOW(),
  revocation_reason = 'workspace_deleted'
WHERE workspace_id = 'ws-uuid-...' AND is_current = true;
```

**State Change:**
- Key marked as revoked in audit trail
- Reason explicitly set to "workspace_deleted"
- `expired_at` remains NULL (manual revocation, not expiration)

**Critical:** This happens BEFORE workspace deletion so audit trail is preserved even if workspace record cascades delete

#### Step 4: Delete DevWorkspace CR

**K8s API Call:**
```python
custom_api.delete_namespaced_custom_object(
    group="workspace.devfile.io",
    version="v1alpha2",
    namespace="devworkspace-treddy",
    plural="devworkspaces",
    name="ph-abc123ef"
)
```

**Result:**
- DevWorkspace CR deleted
- Dev Spaces operator stops reconciliation
- Pod begins termination (graceful shutdown)

#### Step 5: Delete namespace

**K8s API Call:**
```python
core_api.delete_namespace(name="devworkspace-treddy")
```

**Result:**
- Namespace enters "Terminating" state
- All resources cascade delete:
  - Pod
  - PVCs
  - Secrets
  - ConfigMaps
  - ServiceAccounts
- Namespace fully removed after finalizers complete (~5-30s)

#### Step 6: Revoke key from LiteLLM

**HTTP Request:**
```http
POST https://litellm.example.com/key/delete
Authorization: Bearer {litellm_master_key}

{
  "keys": ["key_m4n5o6p7q8r9"]
}
```

**Response:**
```http
200 OK
```

**State Change on LiteLLM:**
- Key immediately disabled
- All API calls with this key return 401 Unauthorized
- Key removed from active keys table
- Key permanently deleted from LiteLLM database
- No longer counts against quotas

#### Step 7: Commit database changes

**Database Transaction:**
```sql
COMMIT;  -- Commits the key_history update from Step 3
```

**Critical:** Key history is committed BEFORE workspace deletion, ensuring audit trail is preserved

#### Step 8: Delete workspace record

**Database Delete:**
```sql
DELETE FROM workspaces WHERE id = 'ws-uuid-...';
```

**Cascade Behavior (depends on FK constraint):**

**Option A: CASCADE (current spec)**
```sql
-- Also deletes all workspace_key_history records
-- Audit trail is lost
```

**Option B: SET NULL (recommended for production)**
```sql
-- workspace_key_history.workspace_id set to NULL
-- Audit trail preserved (orphaned but queryable)
```

#### Step 9: Return success

**HTTP Response:**
```http
204 No Content
```

**Browser Action:**
- Removes workspace button
- Shows "Launch Workspace" instead

### Final State

| System | State |
|--------|-------|
| **LiteLLM** | Key permanently deleted, returns 401 on use |
| **K8s** | Namespace + DevWorkspace + Pod deleted |
| **Database (workspace)** | Record deleted |
| **Database (key_history)** | Preserved (if SET NULL) or deleted (if CASCADE) |

### Duration

**End-to-end:** ~10-30 seconds
- Database update (key revocation): ~50ms
- DevWorkspace CR deletion: ~1s
- Namespace deletion: ~5-30s (depends on finalizers)
- LiteLLM key revocation: ~500ms
- Database workspace deletion: ~50ms

### Audit Trail Result (SET NULL FK)

```sql
SELECT * FROM workspace_key_history 
WHERE maas_key_alias = 'ph-treddy-abc123ef'
ORDER BY provisioned_at DESC;
```

| maas_key_id | workspace_id | is_current | provisioned_at | expired_at | revoked_at | revocation_reason |
|-------------|--------------|------------|----------------|------------|------------|-------------------|
| key_m4n5o6p7q8r9 | NULL | false | 2026-06-29 12:05 | NULL | 2026-06-29 14:30 | workspace_deleted |
| key_f8g9h0i1j2k3 | NULL | false | 2026-05-30 12:00 | 2026-06-29 12:05 | 2026-06-29 12:05 | expired |

**Interpretation:**
- Both keys preserved in audit trail
- `workspace_id` is NULL (workspace deleted)
- Can still query: "Show all keys for user treddy" or "Show keys provisioned for project abc123ef"

---

## 5. Get Key History (Audit)

**User Action:** Administrator views key rotation history for compliance audit

**Preconditions:**
- Workspace exists (or existed and was deleted)
- Key history records exist

### Flow Diagram

```
┌─────────┐     ┌──────────┐     ┌──────────┐
│ Browser │────▶│ Portal   │────▶│ Database │
│         │     │ Backend  │     │          │
└─────────┘     └──────────┘     └──────────┘
     │                │                │
     │  GET /workspace/key-history    │
     ├───────────────▶│                │
     │                │                │
     │                │  SELECT key_history records
     │                ├────────────────▶│
     │                │◀────────────────┤
     │                │  [records]      │
     │                │                │
     │  [key_history] │                │
     │◀───────────────┤                │
```

### Step-by-Step Execution

#### Step 1: Request key history

**Browser:**
```javascript
GET /api/v1/projects/{project_id}/workspace/key-history
```

#### Step 2: Backend queries database

**Database Query:**
```sql
SELECT 
  h.maas_key_id,
  h.maas_key_alias,
  h.provisioned_at,
  h.expired_at,
  h.revoked_at,
  h.revocation_reason,
  h.duration,
  h.models,
  h.is_current
FROM workspace_key_history h
JOIN workspaces w ON w.id = h.workspace_id
WHERE w.project_id = {uuid} AND w.user_id = 'treddy'
ORDER BY h.provisioned_at DESC;
```

**Result:**
```json
[
  {
    "maas_key_id": "key_m4n5o6p7q8r9",
    "maas_key_alias": "ph-treddy-abc123ef",
    "provisioned_at": "2026-06-29T12:05:00Z",
    "expired_at": null,
    "revoked_at": "2026-06-29T14:30:00Z",
    "revocation_reason": "workspace_deleted",
    "duration": "30d",
    "models": ["claude-sonnet-4-5"],
    "is_current": false
  },
  {
    "maas_key_id": "key_f8g9h0i1j2k3",
    "maas_key_alias": "ph-treddy-abc123ef",
    "provisioned_at": "2026-05-30T12:00:00Z",
    "expired_at": "2026-06-29T12:05:00Z",
    "revoked_at": "2026-06-29T12:05:00Z",
    "revocation_reason": "expired",
    "duration": "30d",
    "models": ["claude-sonnet-4-5"],
    "is_current": false
  }
]
```

#### Step 3: Return formatted history

**HTTP Response:**
```json
[
  {
    "maas_key_id": "key_m4n5o6p7q8r9",
    "provisioned_at": "2026-06-29T12:05:00Z",
    "lifecycle": "Manual revocation",
    "reason": "workspace_deleted",
    "lifespan": "2h 25m",
    "models": ["claude-sonnet-4-5"]
  },
  {
    "maas_key_id": "key_f8g9h0i1j2k3",
    "provisioned_at": "2026-05-30T12:00:00Z",
    "lifecycle": "Natural expiration + revocation",
    "reason": "expired",
    "lifespan": "30d 5m",
    "models": ["claude-sonnet-4-5"]
  }
]
```

### Common Audit Queries

**All keys for a user (across all projects):**
```sql
SELECT 
  h.maas_key_alias,
  h.provisioned_at,
  h.revoked_at,
  h.revocation_reason,
  w.project_id
FROM workspace_key_history h
LEFT JOIN workspaces w ON w.id = h.workspace_id
WHERE h.maas_key_alias LIKE 'ph-treddy-%'
ORDER BY h.provisioned_at DESC;
```

**Keys rotated in last 30 days:**
```sql
SELECT COUNT(*), revocation_reason
FROM workspace_key_history
WHERE revoked_at >= NOW() - INTERVAL '30 days'
GROUP BY revocation_reason;
```

**Average key lifespan:**
```sql
SELECT 
  AVG(revoked_at - provisioned_at) AS avg_lifespan,
  revocation_reason
FROM workspace_key_history
WHERE revoked_at IS NOT NULL
GROUP BY revocation_reason;
```

---

## 6. Error Scenarios

### 6.1 LiteLLM API Unavailable (Workspace Creation)

**Trigger:** LiteLLM endpoint is down during workspace creation

**Flow:**
1. User clicks "Launch Workspace"
2. Backend calls `POST /key/generate`
3. Request times out or returns 503 Service Unavailable

**Response:**
```http
500 Internal Server Error
{
  "error": "Failed to provision MaaS key",
  "detail": "LiteLLM service unavailable. Please try again later.",
  "retry_after": 60
}
```

**State:**
- No workspace created
- No database records
- No K8s resources
- User can retry immediately

**Recovery:** Automatic (retry creates workspace from scratch)

---

### 6.2 DevWorkspace Creation Fails (K8s Error)

**Trigger:** K8s rejects DevWorkspace CR (quota exceeded, image pull error, etc.)

**Flow:**
1. User clicks "Launch Workspace"
2. MaaS key provisioned successfully
3. DevWorkspace CR creation fails

**Response:**
```http
500 Internal Server Error
{
  "error": "Failed to create workspace",
  "detail": "Kubernetes quota exceeded: cpu limit reached",
  "provisioned_key_id": "key_abc123"
}
```

**State:**
- MaaS key provisioned (orphaned)
- No workspace in database
- No DevWorkspace CR

**Recovery:**
```python
# Manual cleanup (or automated background job)
await litellm.revoke_key("key_abc123")
```

**Prevention:** Pre-flight quota check before provisioning key

---

### 6.3 Key Rotation Fails Mid-Process

**Trigger:** New key provisioned, but K8s patch fails

**Flow:**
1. User resumes workspace with expired key
2. New key provisioned successfully
3. DevWorkspace env var update fails (K8s API error)

**State:**
- Old key: marked expired + revoked in database
- New key: provisioned in LiteLLM, recorded in database
- DevWorkspace: still has old (revoked) key in env

**Response:**
```http
500 Internal Server Error
{
  "error": "Key rotation incomplete",
  "detail": "New key provisioned but workspace update failed. Contact support.",
  "new_key_id": "key_xyz789"
}
```

**Recovery (Manual):**
1. Admin patches DevWorkspace manually with new key
2. OR: User deletes workspace, recreates (gets new key automatically)

**Prevention:** Transaction-like operation (provision key → update workspace → commit DB atomically)

---

### 6.4 Workspace Deleted But Key Revocation Fails

**Trigger:** LiteLLM API fails during workspace deletion

**Flow:**
1. User deletes workspace
2. Key marked as revoked in database
3. DevWorkspace + namespace deleted successfully
4. LiteLLM `/key/delete` fails (network error, service down)

**State:**
- K8s: Workspace deleted
- Database: Key marked as revoked (audit trail preserved)
- LiteLLM: Key still active (not deleted)

**Impact:**
- Orphaned active key in LiteLLM
- Key will expire naturally after 30 days
- No security risk (workspace gone, user can't access key)

**Recovery (Background Job):**
```python
# Daily cleanup job
orphaned_keys = db.query(WorkspaceKeyHistory).filter(
    WorkspaceKeyHistory.revoked_at.isnot(None),
    WorkspaceKeyHistory.workspace_id.is_(None)  # Workspace deleted
).all()

for key in orphaned_keys:
    try:
        await litellm.revoke_key(key.maas_key_id)
    except:
        pass  # Already deleted or expired
```

---

### 6.5 Database Transaction Rollback

**Trigger:** Database constraint violation during workspace creation

**Flow:**
1. User clicks "Launch Workspace"
2. MaaS key provisioned
3. DevWorkspace created
4. Database insert fails (unique constraint violation: workspace already exists)

**Response:**
```http
409 Conflict
{
  "error": "Workspace already exists",
  "detail": "A workspace for this project already exists. Use 'Open Workspace' instead."
}
```

**State:**
- MaaS key: provisioned (orphaned)
- DevWorkspace: created (orphaned)
- Database: no records (transaction rolled back)

**Recovery:**
```python
# Cleanup orphaned resources
await litellm.revoke_key(key_id)
await devspaces.delete_workspace(namespace, name)
```

**Prevention:** Check for existing workspace BEFORE provisioning key

---

## Summary

### Key Workflow Patterns

1. **Create:** Provision key → Create K8s resources → Record in database
2. **Resume (valid key):** Database lookup → Redirect
3. **Resume (expired key):** Validate → Mark expired → Provision new → Update K8s → Revoke old
4. **Delete:** Mark revoked → Delete K8s → Revoke from LiteLLM → Delete database
5. **Audit:** Database query → Return history

### Critical Ordering

**Creation:**
```
Key provision → K8s creation → DB insert
```

**Rotation:**
```
Mark old expired → Provision new → Update workspace → Revoke old → Update DB
```

**Deletion:**
```
Mark revoked in DB → Delete K8s → Revoke from LiteLLM → Delete DB record
```

### Idempotency

| Operation | Idempotent? | Safe to Retry? |
|-----------|-------------|----------------|
| Create workspace | No | Check existence first |
| Resume workspace | Yes | Multiple calls OK |
| Rotate key | No | Check current key state |
| Delete workspace | Yes | 404 if already gone |
| Get history | Yes | Read-only |

### Duration SLAs

| Workflow | Target | Acceptable |
|----------|--------|------------|
| Create workspace | 45s | 60s |
| Resume (valid key) | 10s | 20s |
| Resume (expired key) | 15s | 30s |
| Delete workspace | 10s | 30s |
| Get key history | <1s | 2s |

---

**End of Workflow Documentation**
