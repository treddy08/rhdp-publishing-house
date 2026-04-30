---
phase: 01-rcars-mcp-gateway
plan: 05
subsystem: infra
tags: [ansible, openshift, route, secret, volume-mount, jinja2, k8s]

# Dependency graph
requires:
  - phase: 01-02
    provides: RCARS HTTP client with rcars_internal_url config setting
  - phase: 01-03
    provides: API key auth middleware expecting MCP_API_KEY_FILE env var
provides:
  - MCP Route (edge TLS, /mcp path only) in Ansible infra template
  - API key Secret (SHA-256 hashed keys) volume-mounted at /etc/ph/mcp-api-keys/keys.yaml
  - RCARS_INTERNAL_URL and MCP_API_KEY_FILE env vars in backend deployment
  - dev.yml.example with MCP and RCARS configuration documentation
  - Cross-namespace connectivity verified (publishing-house-dev to rcars-dev)
affects: [01-06, 01-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [Jinja2 conditional resource blocks with is defined guards, Secret volume mount with defaultMode 0400, per-component build tags replacing webhook triggers, parameterized resource limits via common.yml]

key-files:
  created:
    - rhdp-publishing-house-portal/ansible/tasks/build-backend.yml
    - rhdp-publishing-house-portal/ansible/tasks/build-frontend.yml
  modified:
    - rhdp-publishing-house-portal/ansible/templates/manifests-infra.yaml.j2
    - rhdp-publishing-house-portal/ansible/templates/manifests-app.yaml.j2
    - rhdp-publishing-house-portal/ansible/vars/dev.yml.example
    - rhdp-publishing-house-portal/ansible/deploy.yml
    - rhdp-publishing-house-portal/ansible/tasks/mgmt-rbac.yml
    - rhdp-publishing-house-portal/ansible/tasks/wait-for-builds.yml
    - rhdp-publishing-house-portal/ansible/vars/common.yml

key-decisions:
  - "MCP Route targets backend service on backend_port with 180s timeout (120s RCARS advisor polling + network overhead)"
  - "API key Secret uses stringData with sha256: prefix (Ansible dict2items iterates mcp_api_keys dict)"
  - "Webhook-triggered builds removed in favor of per-component build tags (build_backend, build_frontend)"
  - "Resource limits parameterized in common.yml instead of hardcoded in templates"

patterns-established:
  - "Conditional K8s resource pattern: {% if var is defined and var %} wraps entire resource block, renders only when var is set in Ansible vars"
  - "Secret volume mount pattern: Secret -> Volume (defaultMode 0400) -> VolumeMount (readOnly true) -> env var pointing to mount path"
  - "Per-component build tags: ansible-playbook deploy.yml --tags build_backend to rebuild only the backend"

requirements-completed: [MCP-08, RCARS-04]

# Metrics
duration: 45min
completed: 2026-04-30
---

# Phase 01 Plan 05: Ansible Infrastructure (Route, Secret, Volume Mount) Summary

**MCP Route, API key Secret, volume mount, and RCARS env vars in Ansible deployer templates with cross-namespace connectivity verified on cluster**

## Performance

- **Duration:** 45 min (includes checkpoint verification and deviation fixes)
- **Started:** 2026-04-30T11:10:00Z
- **Completed:** 2026-04-30T12:00:00Z
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify)
- **Files created:** 2
- **Files modified:** 8

## Accomplishments

- MCP Route exposes only /mcp path externally with edge TLS and 180s timeout in manifests-infra.yaml.j2
- API key Secret is volume-mounted into backend pod at /etc/ph/mcp-api-keys/keys.yaml with 0400 permissions
- Backend deployment has RCARS_INTERNAL_URL and MCP_API_KEY_FILE env vars, both conditionally rendered
- Cross-namespace connectivity verified: health endpoint returns {"status":"ok","rcars":{"status":"ok"}}
- Ansible deployer hardcoded values fixed and build system modernized (webhooks removed, per-component tags added)

## Task Commits

Each task was committed atomically (in rhdp-publishing-house-portal repo):

1. **Task 1: MCP Route + API key Secret in infra template** - `fa577bd` (feat)
2. **Task 2: Volume mount + env vars in app template + dev.yml.example** - `f4c14dd` (feat)
3. **Task 3: Checkpoint verified** - approved by user after cluster deployment

### Post-checkpoint deviation fixes (in rhdp-publishing-house-portal repo):

4. **Webhook removal + per-component build tags** - `f55f0ac` (fix)
5. **Missing rcars_url in dev.yml.example** - `ec729c8` (fix)
6. **Hardcoded values fixed + resource limits parameterized** - `86b5454` (fix)
7. **Broken restart tasks removed from wait-for-builds** - `4f6961f` (fix)
8. **Build history limits added to BuildConfigs** - `e732c4d` (fix)

## Files Created/Modified

### Portal repo (rhdp-publishing-house-portal)

- `ansible/templates/manifests-infra.yaml.j2` -- MCP Route and API key Secret resources added; webhook BuildConfigs removed; build history limits added
- `ansible/templates/manifests-app.yaml.j2` -- RCARS_INTERNAL_URL and MCP_API_KEY_FILE env vars; mcp-api-keys volume mount with defaultMode 0400; resource limits parameterized
- `ansible/vars/dev.yml.example` -- mcp_route_host, mcp_api_keys, rcars_internal_url, rcars_url examples with key generation instructions
- `ansible/deploy.yml` -- Per-component build tags (build_backend, build_frontend); webhook tasks removed
- `ansible/tasks/build-backend.yml` -- New task file for backend-only builds
- `ansible/tasks/build-frontend.yml` -- New task file for frontend-only builds
- `ansible/tasks/mgmt-rbac.yml` -- Hardcoded namespace removed, uses app_namespace variable
- `ansible/tasks/wait-for-builds.yml` -- Broken restart tasks removed, simplified to build monitoring only
- `ansible/vars/common.yml` -- Resource limits (cpu/memory for backend, frontend, oauth-proxy) parameterized as defaults
- `ansible/tasks/webhooks.yml` -- DELETED (replaced by per-component build tags)

## Decisions Made

- MCP Route targets backend service directly on backend_port with 180s timeout -- longer than default 30s to accommodate RCARS advisor polling (120s timeout + network overhead)
- API key Secret uses stringData with sha256: prefix -- Jinja2 dict2items filter iterates mcp_api_keys dictionary, no base64 encoding needed
- Webhook-triggered builds were removed during checkpoint review -- they were non-functional and replaced with per-component Ansible tags for selective rebuilds
- Resource limits moved from hardcoded template values to common.yml defaults -- allows environment-specific overrides without template changes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed non-functional webhook BuildConfig triggers**
- **Found during:** Checkpoint review (deployment testing)
- **Issue:** Webhook triggers in BuildConfigs were generating random secrets on every deploy, causing unnecessary rebuilds. They were never actually used for CI/CD.
- **Fix:** Removed webhook BuildConfig resources entirely from manifests-infra.yaml.j2; removed ansible/tasks/webhooks.yml; added per-component build tags (build_backend, build_frontend) to deploy.yml
- **Files modified:** manifests-infra.yaml.j2, deploy.yml, tasks/webhooks.yml (deleted), tasks/build-backend.yml (new), tasks/build-frontend.yml (new)
- **Committed in:** `f55f0ac`

**2. [Rule 1 - Bug] Fixed hardcoded namespace in mgmt-rbac.yml**
- **Found during:** Checkpoint review (deployment testing)
- **Issue:** mgmt-rbac.yml had hardcoded namespace references instead of using the app_namespace variable, causing failures when deploying to non-default namespaces
- **Fix:** Replaced hardcoded namespace with {{ app_namespace }} variable; also parameterized resource limits in manifests-app.yaml.j2 into common.yml defaults
- **Files modified:** tasks/mgmt-rbac.yml, templates/manifests-app.yaml.j2, vars/common.yml
- **Committed in:** `86b5454`

**3. [Rule 1 - Bug] Removed broken restart tasks from wait-for-builds**
- **Found during:** Checkpoint review (deployment testing)
- **Issue:** wait-for-builds.yml contained restart logic that referenced deployment names incorrectly, causing task failures during build monitoring
- **Fix:** Simplified to build-monitoring-only tasks, removing the broken restart logic
- **Files modified:** tasks/wait-for-builds.yml
- **Committed in:** `4f6961f`

**4. [Rule 2 - Missing Critical] Added build history limits**
- **Found during:** Checkpoint review (deployment testing)
- **Issue:** BuildConfigs had no build history limits, allowing unbounded accumulation of completed and failed build records in the namespace
- **Fix:** Added successfulBuildsHistoryLimit: 2 and failedBuildsHistoryLimit: 2 to both backend and frontend BuildConfigs
- **Files modified:** manifests-infra.yaml.j2
- **Committed in:** `e732c4d`

**5. [Rule 1 - Bug] Fixed rcars_url doubled apps. prefix**
- **Found during:** Checkpoint review (dev.yml.example review)
- **Issue:** dev.yml.example was missing rcars_url entry; when added, the existing template referenced rcars_url which was missing from example vars
- **Fix:** Added rcars_url to dev.yml.example with proper cluster domain placeholder
- **Files modified:** vars/dev.yml.example
- **Committed in:** `ec729c8`

---

**Total deviations:** 5 auto-fixed (4 bugs, 1 missing critical)
**Impact on plan:** All fixes were necessary for a working deployment. Webhook removal and build history limits are infrastructure hygiene that would have caused issues on every subsequent deploy. No scope creep -- all changes are within the Ansible deployer scope of this plan.

## Issues Encountered

- Initial deployment required iterative fixes to the Ansible deployer (webhooks, hardcoded values, restart logic) -- these were pre-existing issues in the Ansible templates that surfaced during the first real deployment test with the new MCP resources. All resolved during the checkpoint review cycle.

## User Setup Required

Per the plan's user_setup section, the following manual steps were completed during the checkpoint:

1. **PH Ansible deployer** -- Run to apply Route, Secret, and env var changes to the cluster
2. **RCARS Ansible deployer** -- Run to apply SA allowlist change from Plan 01
3. **Cross-namespace connectivity** -- Verified via health endpoint returning RCARS status "ok"

For future deployments:
- `cd rhdp-publishing-house-portal/ansible && ansible-playbook deploy.yml -e @vars/dev.yml`
- Use `--tags build_backend` or `--tags build_frontend` for selective rebuilds

## Next Phase Readiness

- MCP endpoint is live and accessible via the Route (edge TLS, /mcp path)
- API key Secret is mounted and the auth middleware is operational
- RCARS connectivity is verified end-to-end through the health endpoint
- Plan 06 (intake skill vetting update) can proceed -- the MCP tools are deployed and reachable
- Plan 07 (documentation) can proceed -- all infrastructure is in place

## Self-Check: PASSED

- All 9 created/modified files exist on disk in rhdp-publishing-house-portal
- webhooks.yml confirmed deleted (intentional removal)
- Commit fa577bd (Task 1: MCP Route + Secret) found in git log
- Commit f4c14dd (Task 2: volume mount + env vars) found in git log
- Commit f55f0ac (deviation: webhook removal) found in git log
- Commit ec729c8 (deviation: rcars_url fix) found in git log
- Commit 86b5454 (deviation: hardcoded values) found in git log
- Commit 4f6961f (deviation: wait-for-builds fix) found in git log
- Commit e732c4d (deviation: build history limits) found in git log
- SUMMARY.md exists at .planning/phases/01-rcars-mcp-gateway/01-05-SUMMARY.md

---
*Phase: 01-rcars-mcp-gateway*
*Completed: 2026-04-30*
