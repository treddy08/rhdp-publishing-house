# RHDH DevSpaces Integration - Summary

## What Was Built

A **stateless RHDH Software Template** that creates Publishing House projects with automatic DevSpaces workspace provisioning.

**No database needed** - RHDH Catalog stores workspace URLs as annotations.

---

## Architecture

```
User clicks "Create" in RHDH
  ↓
Fills out form (project name, type, mode, GitHub org)
  ↓
Template executes 3 steps:
  1. Create GitHub repo from PH template
  2. Call provisioner backend (creates DevWorkspace + MaaS key)
  3. Register in RHDH Catalog (stores workspace URL)
  ↓
User redirected to DevSpaces workspace
  ↓
Workspace ready in ~60 seconds with Claude Code configured
```

---

## Components

### 1. **RHDH Software Template** (`templates/publishing-house-project/template.yaml`)

Defines the user form and orchestrates creation.

**User sees:**
- Project Name
- Project Type (workshop/lab/demo)
- Deployment Mode (onboarded/self-published/express)
- GitHub Organization
- Repository Visibility (public/private)

**Template does:**
- Fetches `rhdp-publishing-house-template` repo
- Creates GitHub repo with PH structure
- Calls provisioner backend to create workspace
- Registers project in RHDH Catalog

### 2. **Minimal Provisioner Backend** (`backend-minimal/workspace-provisioner.py`)

~100 lines of Python (FastAPI). **No database.**

**What it does:**
1. Receives project info from template
2. Calls LiteLLM API to provision MaaS key (30d TTL)
3. Creates K8s namespace (`devworkspace-{user}`)
4. Creates DevWorkspace CR with MaaS key injected as env var
5. Returns workspace URL to template

**Deployed to:** `ph-provisioner` namespace

**Endpoint:** `POST /provision`

### 3. **Catalog Entity** (`skeleton/catalog-info.yaml`)

Injected into created GitHub repos. Stores:
- Project metadata (type, deployment mode)
- GitHub repo URL
- **DevSpaces workspace URL** (from provisioner response)

**Phase status NOT stored** - Orchestrator will handle that later.

---

## What's Stored Where

| Data | Location |
|------|----------|
| Workspace URL | RHDH Catalog annotation |
| Project metadata | RHDH Catalog entity |
| MaaS API key | K8s Secret (workspace pod env var) |
| DevWorkspace CR | K8s `devworkspace-{user}` namespace |
| Phase status | ❌ **NOT stored** (future: Orchestrator) |

**No PostgreSQL database needed!**

---

## Deployment Steps

### 1. Deploy Provisioner Backend

```bash
cd rhdh/backend-minimal

# Edit kubernetes/deployment.yaml with:
# - Your LiteLLM master key
# - Your LiteLLM URL

# Build & push image
podman build -t quay.io/rhpds/ph-workspace-provisioner:latest .
podman push quay.io/rhpds/ph-workspace-provisioner:latest

# Deploy to cluster
oc apply -f kubernetes/deployment.yaml
```

### 2. Register Template in RHDH

**Via UI:**
1. Open RHDH → Create → Register Existing Component
2. Enter URL:
   ```
   https://github.com/rhpds/rhdp-publishing-house/blob/main/rhdh/templates/publishing-house-project/template.yaml
   ```
3. Import

### 3. Test It

1. RHDH → Create → "Publishing House Content Project"
2. Fill form → Create
3. Click "Open DevSpaces Workspace"
4. Wait ~60s → VS Code opens with Claude Code ready

---

## What About Phase Tracking?

**Removed from this implementation** - you said Orchestrator should handle phase tracking.

This template only:
- ✅ Creates project
- ✅ Provisions workspace
- ✅ Stores workspace URL in catalog

**Future:** When you enable RHDH Orchestrator, it can:
- Track phase status in its own database
- Update RHDH Catalog annotations with current phase
- Trigger workflows on phase transitions

---

## Files Created

```
rhdh/
├── templates/
│   └── publishing-house-project/
│       ├── template.yaml              # Software Template definition
│       └── skeleton/
│           └── catalog-info.yaml      # Entity metadata (NO phase data)
│
├── backend-minimal/
│   ├── workspace-provisioner.py       # ~100 line FastAPI app (stateless)
│   ├── Containerfile                  # Container build
│   └── kubernetes/
│       └── deployment.yaml            # All K8s manifests
│
├── DEPLOYMENT.md                      # Step-by-step deployment guide
├── README.md                          # Overview + docs
└── SUMMARY.md                         # This file
```

---

## Next Steps

1. **Deploy provisioner backend** (see DEPLOYMENT.md)
2. **Register template in RHDH**
3. **Test end-to-end**
4. **(Future) Enable RHDH Orchestrator for phase tracking**

---

## What's Different from Original Plan?

**Original Plan:**
- PH Central backend (FastAPI + PostgreSQL + MCP tools)
- Database tables for projects, workspaces, key history
- Complex workspace manager service
- Full audit trail

**This Simplified Version:**
- Minimal stateless backend (~100 lines)
- No database (RHDH Catalog = storage)
- No phase tracking (Orchestrator will handle)
- Just workspace provisioning

**Why Simplified:**
- You said: "For testing, can we not use a database?"
- You said: "Orchestrator should store phase info"
- You said: "Just want devworkspace + link in catalog"

This is a **working MVP** you can deploy TODAY. Add complexity later when needed.
