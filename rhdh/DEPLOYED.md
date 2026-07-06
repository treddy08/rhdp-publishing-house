# Publishing House RHDH Template - DEPLOYED ✅

**Date:** 2026-07-06  
**Cluster:** cluster-5hfx8.dynamic2.redhatworkshops.io

---

## ✅ What Was Deployed

### 1. Workspace Provisioner Backend

**Namespace:** `ph-provisioner`

**Components:**
- ✅ ServiceAccount: `workspace-provisioner`
- ✅ ClusterRole: `workspace-provisioner` (create namespaces + DevWorkspaces)
- ✅ ClusterRoleBinding: `workspace-provisioner`
- ✅ Secret: `litellm-credentials` (LiteLLM master key)
- ✅ BuildConfig: Binary build from local directory
- ✅ ImageStream: `ph-workspace-provisioner:latest`
- ✅ Deployment: 1 replica, 256Mi RAM, 100m CPU
- ✅ Service: Port 8000
- ✅ Route: HTTPS with edge termination

**Image:** `image-registry.openshift-image-registry.svc:5000/ph-provisioner/ph-workspace-provisioner:latest`

**URL:** https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io

**Health Check:** ✅ Passing
```bash
curl https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/health
# {"status":"ok","service":"ph-workspace-provisioner"}
```

**Environment Variables:**
- `LITELLM_URL`: https://maas-rhdp.apps.maas.redhatworkshops.io/v1/chat/completions
- `LITELLM_MASTER_KEY`: (from Secret)

### 2. RHDH Template Registration

**ConfigMap:** `backstage-developer-hub-app-config` (updated)

**Template Location Added:**
```yaml
catalog:
  locations:
    - type: url
      target: https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml
      rules:
        - allow:
          - Template
```

**RHDH Restart:** ✅ Completed (took ~21 minutes for init + startup)

**Status:** ⏳ Template will appear in catalog after next refresh (~10 seconds)

---

## URLs

| Service | URL |
|---------|-----|
| **RHDH UI** | https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io |
| **Provisioner** | https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io |
| **Template YAML** | https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml |

---

## How to Use

### Option 1: Via RHDH UI (Recommended)

1. **Open RHDH:**
   ```
   https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io
   ```

2. **Click "Create"** in left sidebar

3. **Find "Publishing House Content Project"**
   - May take ~10-60 seconds for catalog to refresh
   - Look for tags: `publishing-house`, `workshop`, `devspaces`

4. **Fill form:**
   - Project Name: "Test Workshop"
   - Project Type: workshop
   - Deployment Mode: Self-Published
   - GitHub Org: rhpds (or your org)
   - Repo Visibility: public

5. **Click "Create"**

6. **Wait ~30-60 seconds:**
   - ✅ GitHub repo created
   - ✅ Workspace provisioned
   - ✅ Registered in catalog

7. **Click "Open DevSpaces Workspace"**

8. **Wait ~45-60 seconds** → VS Code opens with:
   - Claude Code CLI pre-configured
   - MaaS API key (`$MAAS_API_KEY`)
   - Publishing House skills
   - Your project repo cloned

### Option 2: Test Provisioner Directly

```bash
curl -X POST https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/provision \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test-project",
    "user_id": "testuser",
    "user_email": "test@redhat.com",
    "repo_url": "https://github.com/rhpds/test-repo",
    "repo_branch": "main"
  }'
```

**Expected Response:**
```json
{
  "workspace_url": "https://ph-test-project-devworkspace-testuser.apps.cluster-5hfx8.dynamic2.redhatworkshops.io",
  "workspace_name": "ph-test-project",
  "workspace_namespace": "devworkspace-testuser",
  "maas_key_alias": "ph-testuser-test-project",
  "provisioned_at": "2026-07-06T..."
}
```

---

## Verify Deployment

```bash
# Check provisioner pod
oc get pods -n ph-provisioner
# NAME                                    READY   STATUS      RESTARTS   AGE
# workspace-provisioner-df589b659-7lq4n   1/1     Running     0          Xm

# Check provisioner logs
oc logs -n ph-provisioner deployment/workspace-provisioner -f

# Check RHDH pod
oc get pods -n backstage | grep backstage-developer-hub
# backstage-developer-hub-7998c98968-jv2mj   2/2   Running   0   Xm

# Check template in catalog (wait ~10-60s after RHDH restart)
curl -s 'https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/api/catalog/entities?filter=kind=Template' \
  | jq -r '.[] | select(.metadata.name == "publishing-house-project") | .metadata.name'
# publishing-house-project
```

---

## Troubleshooting

### Template doesn't appear in RHDH

**Wait 10-60 seconds** for catalog refresh, then:

```bash
# Force catalog refresh
oc exec -n backstage deployment/backstage-developer-hub -c backstage-backend -- \
  curl -X POST http://localhost:7007/api/catalog/refresh
```

**Check RHDH logs:**
```bash
oc logs -n backstage deployment/backstage-developer-hub -c backstage-backend --tail=100 | grep -i template
```

**Check ConfigMap:**
```bash
oc get configmap backstage-developer-hub-app-config -n backstage -o yaml | grep -A5 publishing-house
```

### Provisioner fails

**Check logs:**
```bash
oc logs -n ph-provisioner deployment/workspace-provisioner --tail=50
```

**Common issues:**
- LiteLLM key invalid → Update Secret: `oc edit secret litellm-credentials -n ph-provisioner`
- DevWorkspace operator not ready → Check: `oc get pods -n openshift-devspaces`
- Permissions issue → Check ClusterRoleBinding

### Workspace doesn't start

**Check DevWorkspace:**
```bash
oc get devworkspaces -A
oc describe devworkspace ph-{project-name} -n devworkspace-{username}
```

**Check DevSpaces operator:**
```bash
oc get pods -n openshift-devspaces
oc logs -n openshift-devspaces deployment/devspaces-operator -f
```

---

## Clean Up (Testing)

```bash
# Delete test workspace
oc delete devworkspace ph-test-project -n devworkspace-testuser
oc delete namespace devworkspace-testuser

# Delete provisioner
oc delete namespace ph-provisioner

# Remove template from RHDH
# (Edit ConfigMap, remove the location, restart deployment)
```

---

## What's Next

1. **Test end-to-end** - Create a project via RHDH UI
2. **Custom UDI Image** - Pre-install Claude Code in base image
3. **MaaS Key Rotation** - Add endpoint to reprovision expired keys
4. **Showroom Integration** - Add lab guide as workspace tab
5. **Workspace Cleanup** - Periodic job to delete idle workspaces

---

## Files Reference

```
rhdp-publishing-house/
├── rhdh/
│   ├── templates/
│   │   └── publishing-house-project/
│   │       ├── template.yaml              ← Registered in RHDH
│   │       └── skeleton/
│   │           └── catalog-info.yaml      ← Injected into created repos
│   ├── backend-minimal/
│   │   ├── workspace-provisioner.py       ← Deployed to ph-provisioner
│   │   ├── Dockerfile                     ← Built into ImageStream
│   │   ├── Containerfile                  ← Original (identical)
│   │   └── kubernetes/
│   │       └── deployment.yaml            ← K8s manifests
│   ├── DEPLOYMENT.md                      ← Deployment guide
│   ├── DEPLOYED.md                        ← This file
│   ├── REGISTER_TEMPLATE.md               ← Template registration guide
│   └── README.md                          ← Overview
```

---

**STATUS:** ✅ Backend deployed, template registered, waiting for catalog refresh
