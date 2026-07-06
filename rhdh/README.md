# RHDH Integration for Publishing House

This directory contains Red Hat Developer Hub (RHDH/Backstage) integrations for Publishing House.

## Directory Structure

```
rhdh/
├── templates/                      # Software Templates
│   └── publishing-house-project/  # PH project creation template
│       ├── template.yaml           # Template definition
│       └── skeleton/               # Files injected into created repos
│           └── catalog-info.yaml   # Backstage entity metadata
└── plugins/                        # Custom RHDH plugins (future)
```

## Software Templates

### Publishing House Project Template

**Location:** `templates/publishing-house-project/template.yaml`

**Purpose:** Create a new Publishing House content project with automatic DevSpaces workspace provisioning.

**Features:**
- ✅ Create new repo from template OR use existing repo
- ✅ Automatic DevSpaces workspace creation
- ✅ MaaS API key provisioning (via PH Central)
- ✅ Claude Code pre-configured in workspace
- ✅ PH skills pre-installed
- ✅ Backstage catalog registration
- ✅ Optional Jira Initiative linking (onboarded projects)

**User Flow:**

1. User clicks "Create Component" in RHDH
2. Selects "Publishing House Content Project" template
3. Answers questions:
   - Project name
   - Create new repo OR use existing
   - Deployment mode (onboarded/self-published/express)
   - GitHub org (if creating new)
   - Jira Initiative (optional, for onboarded)
4. Template executes:
   - Creates GitHub repo from PH template (if new)
   - Calls PH Central REST API to provision workspace
   - Registers project in Backstage Catalog
5. User redirected to DevSpaces workspace (opens in ~60 seconds)

## Deploying Templates to RHDH

### Option 1: Via ConfigMap (Development)

```bash
# Create ConfigMap from template file
oc create configmap ph-template \
  --from-file=template.yaml=templates/publishing-house-project/template.yaml \
  -n backstage

# Mount to RHDH pod (requires Deployment patch)
oc set volume deployment/backstage-developer-hub \
  --add --type=configmap \
  --configmap-name=ph-template \
  --mount-path=/opt/app-root/src/templates/publishing-house \
  -n backstage
```

### Option 2: Via GitHub URL (Recommended)

**After this directory is committed to the main repo:**

1. Navigate to RHDH admin panel
2. Go to "Create" → "Register Existing Component"
3. Enter URL:
   ```
   https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml
   ```
4. Click "Analyze" → "Import"

RHDH will fetch the template from GitHub and register it.

### Option 3: Via app-config.yaml (Production)

Add to RHDH `app-config.yaml`:

```yaml
catalog:
  locations:
    - type: url
      target: https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml
      rules:
        - allow: [Template]
```

## Backend API Requirements

The template calls this PH Central endpoint:

```
POST /api/v1/projects/create-with-workspace
```

**Request body:**
```json
{
  "setup_mode": "create_new" | "use_existing",
  "project_name": "OpenShift AI Workshop",
  "project_type": "workshop" | "lab" | "demo",
  "deployment_mode": "rhdp_published" | "self_published" | "express",
  "repo_url": "https://github.com/rhpds/ocp-ai-workshop",
  "repo_branch": "main",
  "jira_initiative_key": "RHDPCD-25",  // optional
  "owner_email": "user@redhat.com"
}
```

**Response:**
```json
{
  "project_id": "uuid",
  "project_name": "OpenShift AI Workshop",
  "workspace_url": "https://ph-abc123ef-devworkspace-user.apps.cluster/",
  "jira_epic_key": "RHDPCD-200"  // if onboarded
}
```

**Backend implementation required:**

See `docs/superpowers/specs/2026-06-29-devspaces-implementation.md` for full backend implementation details.

This endpoint must:
1. Register project in PH Central database
2. Call LiteLLMClient to provision MaaS key
3. Call DevSpacesClient to create workspace
4. Inject MaaS key as env var in DevWorkspace CR
5. Create Jira Epic (if onboarded)
6. Return workspace URL for redirect

## Testing the Template

### 1. Deploy Template to RHDH

Use Option 2 above (GitHub URL registration) or manually copy to RHDH pod.

### 2. Access RHDH UI

```
https://backstage-backstage.apps.cluster-5hfx8.dynamic2.redhatworkshops.io
```

### 3. Create Component

1. Click "Create" in left sidebar
2. Find "Publishing House Content Project" template
3. Fill out the form
4. Click "Create"

### 4. Verify Workspace

After ~60 seconds, workspace should open in browser VS Code with:
- Claude Code extension loaded
- MaaS API key configured
- PH skills available at `~/rhdp-publishing-house-skills`
- Project repo cloned to `/projects/<repo-name>`

## Customizing the Template

### Add New Questions

Edit `template.yaml` → `spec.parameters`:

```yaml
parameters:
  - title: Your New Section
    properties:
      your_field:
        title: Your Question
        type: string
        enum: [option1, option2]
```

### Add Template Variables

Available in `skeleton/` files via `${{ values.your_field }}`:

- `values.project_name` - User's project name
- `values.deployment_mode` - rhdp_published/self_published/express
- `values.github_org` - GitHub organization
- `user.entity.metadata.name` - Backstage username
- `user.entity.spec.profile.email` - User email

### Conditional Steps

Use `if:` in steps:

```yaml
steps:
  - id: my-step
    if: ${{ parameters.deployment_mode === 'rhdp_published' }}
    action: ...
```

## Troubleshooting

### Template not appearing in RHDH

1. Check RHDH logs:
   ```bash
   oc logs -n backstage deployment/backstage-developer-hub -f
   ```

2. Verify template syntax:
   ```bash
   # Use RHDH template validator
   npx @backstage/cli validate:template template.yaml
   ```

### Workspace creation fails

1. Check PH Central backend logs:
   ```bash
   oc logs -n publishing-house-central-dev deployment/backend -f
   ```

2. Verify endpoint is accessible:
   ```bash
   curl -X POST https://publishing-house-central-dev.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/api/v1/projects/create-with-workspace \
     -H "Content-Type: application/json" \
     -d '{"setup_mode": "use_existing", ...}'
   ```

3. Check DevSpaces operator:
   ```bash
   oc get checluster -n openshift-devspaces
   oc get pods -n openshift-devspaces
   ```

### User email not available

If `user.entity.spec.profile.email` is empty, RHDH may not have user profiles configured.

**Workaround:** Add email input field to template:

```yaml
parameters:
  - title: Contact
    properties:
      owner_email:
        title: Your Email
        type: string
        ui:field: OwnerPicker
```

## Next Steps

Once the template is working:

1. **Create Custom Plugin** - Display PH phase progress in Backstage entity pages
2. **Add Workflow Integration** - Use RHDH Orchestrator for complex provisioning
3. **Add More Templates** - Templates for specific workshop types (AI, GitOps, Security)

## Resources

- [Backstage Software Templates](https://backstage.io/docs/features/software-templates/)
- [RHDH Documentation](https://docs.redhat.com/en/documentation/red_hat_developer_hub/)
- [Publishing House DevSpaces Spec](../docs/superpowers/specs/2026-06-29-devspaces-implementation.md)
