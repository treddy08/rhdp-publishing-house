# HTTP Action Not Available in RHDH

## Problem

The Publishing House template requires the `http:backstage:request` action to call the workspace provisioner API, but this action is not registered in the current RHDH deployment.

**Error:**
```
NotFoundError: Template action with ID 'http:backstage:request' is not registered.
```

## Solution

The RHDH deployment needs to have the HTTP scaffolder action plugin installed.

### Option 1: Add HTTP Action Plugin (Recommended)

Add to RHDH's dynamic plugins configuration:

```yaml
# Add to rhdh-plugins-config ConfigMap or equivalent
plugins:
  - package: '@backstage/plugin-scaffolder-backend-module-http@^0.2.0'
    disabled: false
```

Then restart RHDH:
```bash
oc rollout restart deployment/backstage-developer-hub -n backstage
```

### Option 2: Use Kubernetes Job Instead

Alternative: Create a Kubernetes Job action that runs a container to call the provisioner API.

Change template step from:
```yaml
- id: provision-workspace
  action: http:backstage:request
  input:
    method: POST
    url: https://workspace-provisioner...
```

To:
```yaml
- id: provision-workspace
  action: kubernetes:apply
  input:
    namespaced: true
    manifest: |
      apiVersion: batch/v1
      kind: Job
      metadata:
        name: provision-${{ parameters.project_name }}
        namespace: ph-provisioner
      spec:
        template:
          spec:
            containers:
            - name: curl
              image: curlimages/curl:latest
              command:
                - curl
                - -X
                - POST
                - https://workspace-provisioner-ph-provisioner.apps.cluster-5hfx8.dynamic2.redhatworkshops.io/provision
                - -H
                - "Content-Type: application/json"
                - -d
                - |
                  {
                    "project_name": "${{ parameters.project_name }}",
                    "user_id": "${{ user.entity.metadata.name }}",
                    "user_email": "${{ user.entity.spec.profile.email }}",
                    "repo_url": "${{ parameters.repo_type === 'existing' and parameters.repo_url or steps.publish.output.remoteUrl }}",
                    "repo_branch": "${{ parameters.repo_type === 'existing' and parameters.repo_branch or 'main' }}"
                  }
            restartPolicy: Never
```

But this requires:
1. RHDH ServiceAccount has permissions to create Jobs in ph-provisioner namespace
2. Parsing job output to get workspace URL (complex)

## Current Status

Template is updated to use a temporary workaround, but proper fix requires adding the HTTP action plugin to RHDH.

## Next Steps

1. Contact RHDH admin to add `@backstage/plugin-scaffolder-backend-module-http` plugin
2. OR use the Kubernetes Job workaround above
3. OR move provisioner logic into a custom scaffolder action (more complex)
