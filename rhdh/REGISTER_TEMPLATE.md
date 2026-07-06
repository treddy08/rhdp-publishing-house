# Register Publishing House Template in RHDH

## ✅ Step 1: Backend Deployed

The workspace provisioner backend is running at:
```
https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io
```

Health check: ✅ Passing

---

## Step 2: Register Template in RHDH

### Option A: Via RHDH UI (Recommended)

1. **Open RHDH:**
   ```
   https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io
   ```

2. **Navigate to Register:**
   - Click **"Create"** in the left sidebar
   - Click **"Register Existing Component"** button

3. **Enter Template URL:**
   ```
   https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml
   ```

4. **Import:**
   - Click **"Analyze"**
   - Click **"Import"**

5. **Verify:**
   - Go back to **"Create"**
   - You should see **"Publishing House Content Project"** template

### Option B: Via API (If UI doesn't work)

```bash
# Get RHDH token (from UI: Settings → Authentication)
RHDH_TOKEN="your-token-here"

# Register template
curl -X POST https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/api/catalog/locations \
  -H "Authorization: Bearer $RHDH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url",
    "target": "https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml"
  }'
```

---

## Step 3: Test Creating a Project

1. **Open RHDH Create Page:**
   ```
   https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/create
   ```

2. **Find the Template:**
   - Look for **"Publishing House Content Project"**
   - Tags: `publishing-house`, `workshop`, `devspaces`

3. **Fill Out Form:**
   - **Project Name:** "Test Workshop"
   - **Project Type:** workshop
   - **Deployment Mode:** Self-Published
   - **GitHub Org:** rhpds
   - **Repo Visibility:** public

4. **Create:**
   - Click **"Create"**
   - Watch progress (takes ~30-60 seconds)

5. **Expected Output:**
   - ✅ GitHub repo created: `https://github.com/rhpds/test-workshop`
   - ✅ Workspace provisioned
   - ✅ Registered in catalog
   - ✅ Link to workspace: "Open DevSpaces Workspace"

6. **Launch Workspace:**
   - Click **"Open DevSpaces Workspace"**
   - Wait ~45-60 seconds
   - VS Code opens in browser with:
     - Claude Code CLI pre-configured
     - MaaS API key as `$MAAS_API_KEY` env var
     - Publishing House skills cloned
     - Your project repo cloned

---

## Troubleshooting

### Template doesn't appear in RHDH

**Check RHDH logs:**
```bash
oc logs -n backstage deployment/backstage-developer-hub -f | grep -i template
```

### Provisioner fails

**Check provisioner logs:**
```bash
oc logs -n ph-provisioner deployment/workspace-provisioner -f
```

**Test provisioner manually:**
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

### Workspace doesn't start

**Check DevWorkspace status:**
```bash
oc get devworkspaces -A
oc describe devworkspace ph-test-project -n devworkspace-{username}
```

---

## What's Next?

Once the template is working:

1. **Custom UDI Image** - Build base image with Claude Code pre-installed
2. **Showroom Integration** - Add Showroom lab guide as a workspace tab
3. **MaaS Key Rotation** - Add endpoint to reprovision expired keys
4. **Workspace Cleanup** - Periodic job to delete idle workspaces

---

## URLs Reference

| Service | URL |
|---------|-----|
| **RHDH** | https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io |
| **Provisioner** | https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io |
| **Template YAML** | https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml |
| **LiteLLM** | https://maas-rhdp.apps.maas.redhatworkshops.io/v1/chat/completions |
