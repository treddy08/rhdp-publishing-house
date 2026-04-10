# GitOps Automation Guide

How to create GitOps repos that automate RHDP lab/demo environments using
Helm + ArgoCD. Based on the RHDP GitOps template at
`https://github.com/rhpds/ci-template-gitops`.

## When to Use GitOps vs Ansible

| Use GitOps When | Use Ansible When |
|----------------|------------------|
| Environment is fully declarative (K8s manifests) | Tasks require imperative logic (wait loops, conditionals) |
| Changes should be continuously reconciled | One-time setup is sufficient |
| Multiple environments need the same config | Simple operator install + configure |
| Lab involves GitOps concepts (ArgoCD is the point) | Lab doesn't involve GitOps |

Many labs use both — Ansible for initial cluster setup (operators, auth) and GitOps
for application workloads that benefit from continuous reconciliation.

## Architecture: Three Layers

The GitOps template uses an app-of-apps pattern with three layers:

```
cluster/infra/bootstrap/      → Operators and cluster infrastructure (deployed once)
         ↓ spawns
cluster/platform/bootstrap/   → Shared services for all users (deployed once)

tenant/bootstrap/             → Per-user lab workloads (deployed per user)
```

### Infra Layer (`cluster/infra/bootstrap/`)

- Installs operators (subscriptions, operator groups)
- Creates ArgoCD AppProjects (infra, platform, tenants)
- Spawns the platform bootstrap Application
- Returns cluster-level provision data to RHDP

### Platform Layer (`cluster/platform/bootstrap/`)

- Configures operators installed by infra layer
- Deploys shared services (e.g., GitLab, shared databases)
- Never created directly — spawned by infra bootstrap

### Tenant Layer (`tenant/bootstrap/`)

- Per-user workloads (one ArgoCD Application per user/deployment)
- Three patterns for deploying resources (see below)
- Returns tenant-level provision data to RHDP

## Helm Chart Patterns

Each layer's bootstrap is a Helm chart that creates ArgoCD Applications.

### Values Structure

```yaml
# Anchor for git defaults (reused across workloads)
default_settings: &git_defaults
  repoURL: https://github.com/rhpds/<your-gitops-repo>.git
  targetRevision: main

# Deployer values (injected by Ansible role at deploy time)
deployer:
  domain: apps.cluster-guid.example.com
  apiUrl: https://api.cluster-guid.example.com:6443
  guid: GUID

# Per-workload configuration
myWorkload:
  enabled: false                    # All workloads disabled by default
  namespace: NAMESPACE-MUST-BE-SET  # Fail loud if not overridden
  git:
    path: tenant/labs/my-workload
    <<: *git_defaults
```

### Enable/Disable Pattern

Every workload has an `enabled: false` default. The AgnosticV catalog enables
specific workloads by passing `enabled: true` through Helm values.

```yaml
# In ArgoCD Application template
{{- if .Values.myWorkload.enabled }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-workload-{{ .Values.tenant.name }}
  namespace: openshift-gitops
spec:
  project: tenants
  source:
    repoURL: {{ .Values.myWorkload.git.repoURL }}
    targetRevision: {{ .Values.myWorkload.git.targetRevision }}
    path: {{ .Values.myWorkload.git.path }}
    helm:
      values: |
        deployer: {{ .Values.deployer | toYaml | nindent 10 }}
        tenant: {{ .Values.tenant | toYaml | nindent 10 }}
        myWorkload: {{ .Values.myWorkload | toYaml | nindent 10 }}
  destination:
    server: https://kubernetes.default.svc
    namespace: {{ .Values.myWorkload.namespace }}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - SkipDryRunOnMissingResource=true
      - RespectIgnoreDifferences=true
    retry:
      limit: 10
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
{{- end }}
```

## Three Tenant Deployment Patterns

### Pattern 1: Inline Resources (Simplest)

Resources rendered directly by the bootstrap chart. No sub-chart needed.

```yaml
# tenant/bootstrap/templates/my-inline-resource.yaml
{{- if .Values.myInlineApp.enabled }}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: {{ .Values.myInlineApp.namespace }}  # ALWAYS explicit namespace
spec:
  replicas: 1
  ...
---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: {{ .Values.myInlineApp.namespace }}
spec:
  ...
{{- end }}
```

**Use when:** Simple, one-off resources (a few manifests). No independent sync needed.

**Critical:** Always set explicit `namespace` on every resource. Without it, resources
deploy to `openshift-gitops` (the ArgoCD namespace), not the tenant namespace.

### Pattern 2: Helm Sub-chart (Basic)

Bootstrap creates a child ArgoCD Application pointing at a separate Helm chart.

```
tenant/
├── bootstrap/templates/application-my-app.yaml   # ArgoCD Application
└── my-app/                                       # Helm chart
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── deployment.yaml
        ├── service.yaml
        └── route.yaml
```

**Use when:** Multi-resource workload that benefits from independent sync status.

### Pattern 3: Parameterized Helm Sub-chart (Catalog-Driven)

Like Pattern 2, but all meaningful values are driven from the AgnosticV catalog.

```yaml
# tenant/bootstrap/templates/application-my-lab.yaml
{{- if .Values.labs.myLab.enabled }}
spec:
  source:
    path: tenant/labs/my-lab
    helm:
      values: |
        namespace: {{ .Values.labs.myLab.namespace | quote }}
        message: {{ .Values.labs.myLab.message | quote }}
        replicas: {{ .Values.labs.myLab.replicas }}
{{- end }}
```

**Use when:** Lab workloads where the catalog controls behavior. Namespace is
intentionally set to `NAMESPACE-MUST-BE-SET-BY-CATALOG` in defaults to fail loud
if the catalog doesn't provide it.

## Provision Data

Return connection information to RHDP via labeled ConfigMaps:

```yaml
# In your workload's Helm chart
apiVersion: v1
kind: ConfigMap
metadata:
  name: tenant-{{ .Values.tenant.name }}-my-app-provisiondata
  namespace: {{ .Values.myApp.namespace }}
  labels:
    demo.redhat.com/tenant-{{ .Values.tenant.name }}: "true"
data:
  provision_data: |
    app_url: https://my-app-{{ .Values.myApp.namespace }}.{{ .Values.deployer.domain }}
```

The `demo.redhat.com/tenant-<name>` label tells the RHDP deployer to pick up this data
and surface it to the user.

## AgnosticV Integration

GitOps repos are consumed via the `ocp4_workload_gitops_bootstrap` role:

### Cluster-Level (Infra + Platform)

```yaml
# In AgnosticV common.yaml
workloads:
  - agnosticd.core_workloads.ocp4_workload_gitops_bootstrap

ocp4_workload_gitops_bootstrap_repo_url: https://github.com/rhpds/<your-gitops-repo>.git
ocp4_workload_gitops_bootstrap_repo_revision: main
ocp4_workload_gitops_bootstrap_repo_path: cluster/infra/bootstrap
ocp4_workload_gitops_bootstrap_application_name: bootstrap-infra
ocp4_workload_gitops_bootstrap_application_project: infra

ocp4_workload_gitops_bootstrap_helm_values:
  myOperator:
    enabled: true
  platformValues:
    mySharedService:
      enabled: true
```

### Tenant-Level (Per User)

```yaml
workloads:
  - agnosticd.core_workloads.ocp4_workload_tenant_namespace
  - agnosticd.core_workloads.ocp4_workload_gitops_bootstrap

# Namespace setup (must happen BEFORE GitOps bootstrap)
ocp4_workload_tenant_namespace_username: "user-{{ guid }}"
ocp4_workload_tenant_namespace_suffixes:
  - suffix: my-lab

# GitOps bootstrap
ocp4_workload_gitops_bootstrap_repo_url: https://github.com/rhpds/<your-gitops-repo>.git
ocp4_workload_gitops_bootstrap_repo_revision: main
ocp4_workload_gitops_bootstrap_repo_path: tenant/bootstrap
ocp4_workload_gitops_bootstrap_application_name: "bootstrap-{{ guid }}"
ocp4_workload_gitops_bootstrap_application_project: tenants

ocp4_workload_gitops_bootstrap_helm_values:
  tenant:
    name: "{{ guid }}"
    user:
      name: "{{ ocp4_workload_tenant_keycloak_username }}"
  labs:
    myLab:
      enabled: true
      namespace: "user-{{ guid }}-my-lab"
```

Namespace suffixes must match the namespace values in the Helm chart.

## Creating a New GitOps Repo

1. Clone the template: `gh repo create rhpds/<lab-name>-gitops --template rhpds/ci-template-gitops --private --clone`
2. Remove the examples you don't need from `tenant/bootstrap/templates/`
3. Add your workload chart under `tenant/labs/<your-lab>/`
4. Add an Application template in `tenant/bootstrap/templates/`
5. Add your workload's values block to `tenant/bootstrap/values.yaml`
6. Add provision data ConfigMap to your chart if needed
7. Test with a dev AgnosticV catalog

## Sync Policy Standards

All ArgoCD Applications should use this sync policy:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
    - CreateNamespace=true
    - SkipDryRunOnMissingResource=true    # CRDs appear after operator install
    - RespectIgnoreDifferences=true       # Operators mutate their own fields
  retry:
    limit: 10
    backoff:
      duration: 5s
      factor: 2
      maxDuration: 3m
```

## What to Automate vs What the Learner Does

Same principle as Ansible automation — see the Ansible Automation Guide for the
full decision framework on distinguishing pre-configured environment from learner
exercises.
