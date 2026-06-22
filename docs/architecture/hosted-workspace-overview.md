# Hosted Workspace (Dev Spaces)

!!! info "Proposed"
    This feature is designed but not yet implemented. The design spec is complete and awaiting team review. Prerequisites (Dev Spaces operator installation, custom UDI image build) are blocking deployment.

## The Problem

Publishing House skills run inside Claude Code — a local tool that requires an Anthropic model subscription and a terminal. Not everyone has that. Solution architects, field engineers, and content developers who don't have Claude Code locally can see project status in Central, but they can't do the actual work: running intake, writing content, building automation, or editing modules.

PH needs a hosted execution path that gives these users the same capabilities as someone running Claude Code on their laptop.

## How It Works

### Dev Spaces as the Execution Platform

When a user opens a project in Central and wants to work on it, they click "Open in Dev Spaces." The Central provisions an OpenShift Dev Spaces workspace — a full VS Code environment running in the browser, pre-configured with everything needed to use PH.

The workspace includes:

- **Claude Code** (CLI and VS Code extension) — the AI assistant that powers PH
- **PH skills plugin** — intake, writing, editing, automation, orchestration
- **Developer tooling** — oc CLI, Ansible, git, Python
- **Model access** — an API key for AI model access, provisioned automatically

The user lands in VS Code in their browser. From there, they work exactly as they would on their laptop — Claude Code handles the content lifecycle, PH skills guide the process, and everything commits to git.

```
Central                          Dev Spaces
┌──────────────┐               ┌──────────────────────┐
│ Project view │               │ VS Code (browser)    │
│              │  "Open in     │  ├── CC Extension     │
│  [Open in    │──Dev Spaces──►│  ├── PH Skills        │
│   Dev Spaces]│               │  ├── Terminal (oc,    │
│              │               │  │   ansible, git)    │
└──────┬───────┘               │  └── Project repo     │
       │                       └──────────┬────────────┘
       │          MCP tools               │
       ◄──────────────────────────────────┘
       (workspace calls Central for
        status, RCARS, validation)
```

### What Central Does

Central's role is simple: provision the workspace, link to it, and get out of the way.

- **First visit:** Creates the workspace and provisions an API key for model access. Redirects the user into VS Code.
- **Return visit (workspace running):** Redirects to the existing workspace.
- **Return visit (workspace stopped):** Checks if the API key is still valid, provisions a new one if expired, restarts the workspace, and redirects.
- **Workspace deleted:** Revokes the API key and cleans up the record.

The Central does not manage what happens inside the workspace. Dev Spaces handles persistence, idle timeouts, and resource quotas. The user manages their workspace through the Dev Spaces dashboard if needed.

### One-Way Integration

The workspace calls Central — never the reverse. Claude Code inside the workspace uses PH's MCP tools to check project status, run RCARS queries, store validation results, and sync manifests. The Central reflects these updates on the next page load.

There is no push notification from Central to workspace. No remote orchestration. The Central provisions and links. The workspace does the work. Git is the sync mechanism between them.

### Model Access (MaaS Keys)

Users don't need to bring their own API key. When Central creates a workspace, it automatically provisions a short-lived key through the Model as a Service (MaaS) platform. The key is injected into the workspace as an environment variable — Claude Code picks it up automatically.

Keys have a configurable time-to-live. If a workspace sits idle long enough for the key to expire, the user goes back to Central and clicks "Resume Workspace" — Central provisions a fresh key and restarts the workspace. The user never sees, copies, or manages keys directly.

### What's in the Workspace Image

The workspace runs a custom container image based on the Red Hat Universal Developer Image (UDI, RHEL 9). It ships with Claude Code, PH skills, and all tooling pre-installed. Claude Code updates to the latest version every time a workspace starts — no image rebuild needed for CC updates.

The image is published to `quay.io/rhpds/ph-udi` and rebuilt periodically for security patches and tooling updates.

## Who Does What

| Role | Responsibility |
|------|---------------|
| **Content developers** | Click "Open in Dev Spaces" on their project. Work in VS Code as they would locally. Commit and push when done. |
| **Central** | Provision workspace, provision API key, show workspace link, validate key on resume, revoke key on delete. |
| **Dev Spaces** | Run the workspace pod, manage persistence, handle idle timeout, provide the VS Code server. |
| **Infra team** | Install Dev Spaces operator on the cluster (one-time). Maintain the custom UDI image. |

## What This Does NOT Do

- **Replace local Claude Code.** Users with local CC continue using it. The workspace is for users who don't have local access. Both paths use the same PH skills and produce the same output.
- **Manage workspaces.** The Central links to workspaces. Dev Spaces manages them. There is no workspace list, lifecycle management, or admin panel in Central.
- **Serve non-developer audiences (yet).** Phase 1 targets content developers comfortable with an IDE and terminal. A smoother experience for broader audiences is a future effort.
- **Provide a lightweight express mode.** Dev Spaces workspaces are resource-intensive. A lighter execution option for quick one-off demos is a backlog item.

## Prerequisites

Three things need to happen before this can go live:

1. **Dev Spaces operator.** The OpenShift Dev Spaces operator needs to be installed on the infra cluster. Standard operator install — request from the infra team.

2. **Custom UDI image.** The PH container image needs to be built and pushed to `quay.io/rhpds/ph-udi`. This includes Claude Code, PH skills, Ansible, and the startup script.

3. **MaaS connectivity.** The Central backend needs network access to the LiteLLM (MaaS) API to provision and revoke keys. The LiteLLM master key needs to be stored as an OpenShift Secret.
