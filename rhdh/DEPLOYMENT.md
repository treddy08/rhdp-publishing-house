# Deploying Publishing House RHDH Template

**Goal:** Enable users to click "Create" in RHDH → fill out a form → get a DevSpaces workspace with Claude Code ready in ~60 seconds.

**Architecture:** Stateless - RHDH Catalog stores workspace URLs as annotations, no database needed.

---

## Prerequisites on Your Cluster

✅ **Already exist:**
- RHDH (Backstage) - `backstage` namespace
- DevSpaces Operator - `openshift-devspaces` namespace

❌ **Need to deploy:**
- Minimal workspace provisioner backend (~100 lines Python)

---

## Step 1: Deploy Minimal Backend

This tiny service just provisions MaaS keys and creates DevWorkspace CRs. No database.

### 1.1. Update the Secret

Edit `rhdh/backend-minimal/kubernetes/deployment.yaml`:

```yaml
stringData:
  master-key: "YOUR_LITELLM_MASTER_KEY_HERE"
```

And update LiteLLM URL:

```yaml
env:
  - name: LITELLM_URL
    value: "https://your-litellm-instance.com"  # ← Change this
```

### 1.2. Build and Push Image

```bash
cd rhdh/backend-minimal

# Build
podman build -t quay.io/rhpds/ph-workspace-provisioner:latest -f Containerfile .

# Push
podman push quay.io/rhpds/ph-workspace-provisioner:latest
```

### 1.3. Deploy to Cluster

```bash
# Login to cluster
oc login --server=https://api.cluster-5hfx8.dynamic2.redhatworkshops.io:6443 \
  --username=admin \
  --password=LwXqrEJzuqfG

# Apply manifests
oc apply -f kubernetes/deployment.yaml

# Verify deployment
oc get pods -n ph-provisioner
oc logs -n ph-provisioner deployment/workspace-provisioner -f

# Get route URL
oc get route -n ph-provisioner workspace-provisioner -o jsonpath='{.spec.host}'
```

**Expected output:**
```
workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io
```

### 1.4. Test the Endpoint

```bash
PROVISIONER_URL=$(oc get route -n ph-provisioner workspace-provisioner -o jsonpath='{.spec.host}')

curl -X POST https://$PROVISIONER_URL/provision \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test-project",
    "user_id": "testuser",
    "user_email": "test@redhat.com",
    "repo_url": "https://github.com/rhpds/test-repo",
    "repo_branch": "main"
  }'
```

**Expected response:**
```json
{
  "workspace_url": "https://ph-test-project-devworkspace-testuser.apps.cluster-5hfx8.dynamic2.redhatworkshops.io",
  "workspace_name": "ph-test-project",
  "workspace_namespace": "devworkspace-testuser",
  "maas_key_alias": "ph-testuser-test-project",
  "provisioned_at": "2026-07-06T12:34:56.789Z"
}
```

---

## Step 2: Register Template in RHDH

### Option A: Via GitHub URL (Recommended)

1. Open RHDH: `https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io`

2. Navigate: **Create** → **Register Existing Component**

3. Enter URL:
   ```
   https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml
   ```

4. Click **Analyze** → **Import**

5. Template appears in "Create" menu

### Option B: Via ConfigMap

```bash
oc create configmap ph-template \
  --from-file=template.yaml=templates/publishing-house-project/template.yaml \
  -n backstage

# Restart RHDH to pick up template
oc rollout restart deployment/backstage-developer-hub -n backstage
```

---

## Step 3: Test End-to-End

### 3.1. Create Project via RHDH

1. Open RHDH UI
2. Click **Create** (left sidebar)
3. Find **"Publishing House Content Project"** template
4. Fill out form:
   - **Project Name:** Test Workshop
   - **Project Type:** workshop
   - **Deployment Mode:** Self-Published
   - **GitHub Org:** rhpds
   - **Visibility:** public
5. Click **Create**

### 3.2. Wait for Provisioning

Progress shown in RHDH:
- ✅ Fetch template
- ✅ Create GitHub repo
- ✅ Provision workspace (calls provisioner backend)
- ✅ Register in catalog

### 3.3. Launch Workspace

After ~10 seconds, RHDH shows:
- **"Open DevSpaces Workspace"** link
- Click it → DevSpaces starts workspace

Wait ~45-60 seconds → VS Code opens in browser

### 3.4. Verify Workspace

In the browser VS Code:

1. **Check Claude Code extension** - Should be loaded
2. **Check MaaS key:**
   ```bash
   echo $MAAS_API_KEY  # Should show sk-...
   ```
3. **Check PH skills:**
   ```bash
   ls ~/rhdp-publishing-house-skills
   ```
4. **Check project repo:**
   ```bash
   ls /projects/test-workshop
   ```

---

## Architecture Diagram

```
User → RHDH Template Form
          ↓
       1. Create GitHub repo (template action)
          ↓
       2. Call provisioner backend:
          POST /provision
          ↓
       ┌─────────────────────────────────┐
       │ Provisioner Backend (Stateless) │
       │ - Call LiteLLM API (MaaS key)   │
       │ - Create K8s namespace          │
       │ - Create DevWorkspace CR        │
       │ - Return workspace URL          │
       └─────────────────────────────────┘
          ↓
       3. Register in RHDH Catalog
          (stores workspace URL as annotation)
          ↓
       4. Redirect to workspace URL
          ↓
       User lands in VS Code (~60s)
```

---

## What's Stored Where

| Data | Storage Location |
|------|------------------|
| **Workspace URL** | RHDH Catalog annotation |
| **MaaS key alias** | RHDH Catalog annotation |
| **Project metadata** | RHDH Catalog (name, type, mode) |
| **Actual MaaS key** | K8s Secret (env var in workspace pod) |
| **DevWorkspace CR** | K8s `devworkspace-{user}` namespace |
| **Phase status** | ❌ NOT STORED (Orchestrator will handle) |

**NO DATABASE** - Everything is either in RHDH Catalog or Kubernetes.

---

## Troubleshooting

### Template doesn't appear in RHDH

**Check RHDH logs:**
```bash
oc logs -n backstage deployment/backstage-developer-hub -f | grep -i template
```

**Verify template syntax:**
```bash
# Use RHDH validator
npx @backstage/cli validate:template templates/publishing-house-project/template.yaml
```

### Provisioner backend fails

**Check logs:**
```bash
oc logs -n ph-provisioner deployment/workspace-provisioner -f
```

**Common issues:**
- LiteLLM master key wrong/missing → Check Secret
- K8s permissions wrong → Check ClusterRole/ClusterRoleBinding
- DevWorkspace CRD not found → Check DevSpaces operator installed

### Workspace doesn't start

**Check DevWorkspace status:**
```bash
oc get devworkspaces -n devworkspace-{username}
oc describe devworkspace ph-{project-name} -n devworkspace-{username}
```

**Check DevSpaces operator:**
```bash
oc get pods -n openshift-devspaces
oc logs -n openshift-devspaces deployment/devspaces -f
```

---

## What's Next

After this works:

1. **Custom UDI Image** - Build `quay.io/rhpds/publishing-house-udi` with Claude Code pre-installed
2. **MaaS Key Rotation** - Add endpoint to reprovision expired keys
3. **Workspace Cleanup** - Periodic job to delete idle workspaces
4. **Custom RHDH Plugin** - Display workspace status in catalog

---

## Clean Up (Testing)

```bash
# Delete test workspace
oc delete devworkspace ph-test-project -n devworkspace-testuser
oc delete namespace devworkspace-testuser

# Delete provisioner
oc delete namespace ph-provisioner

# Unregister template from RHDH
# (Delete via RHDH UI → Catalog → Filter: kind=Template → Delete)
```

---

## Files Reference

```
rhdh/
├── templates/
│   └── publishing-house-project/
│       ├── template.yaml           # RHDH Software Template
│       └── skeleton/
│           └── catalog-info.yaml   # Injected into created repos
├── backend-minimal/
│   ├── workspace-provisioner.py    # ~100 line FastAPI app
│   ├── Containerfile               # Container build
│   └── kubernetes/
│       └── deployment.yaml         # K8s manifests
├── DEPLOYMENT.md                   # This file
└── README.md                       # Overview
```
