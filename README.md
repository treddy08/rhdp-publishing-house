# RHDP Publishing House

AI-powered content lifecycle management for Red Hat Demo Platform.

## Overview

One command — `/rhdp-publishing-house` — provides a persistent, state-aware orchestrator
that manages the entire content lifecycle through specialized AI agents. Content developers
become content architects: design the architecture, agents handle the writing, editing,
automation, and review.

## Skills

### /rhdp-publishing-house (orchestrator)

Entry point. Discovers your project from any directory, syncs the repo, reads the manifest,
presents current state, and dispatches agent skills. Supports three autonomy levels:
supervised (default), semi, full.

### /rhdp-publishing-house:intake

Spec generation, RCARS vetting, and spec refinement. Three intake paths:

- **Full spec provided** — agent fills gaps, normalizes format
- **Rough idea** — agent builds spec through conversation
- **RCARS gap** — gap description becomes seed for new spec

Also handles: deployment mode selection, Showroom and automation repo setup.

### /rhdp-publishing-house:writer

Content writing agent. Wraps `showroom:create-lab` (workshops) and `showroom:create-demo`
(demos) to generate Showroom AsciiDoc from approved module outlines. Works module-by-module,
respects human edits.

### /rhdp-publishing-house:editor

Technical editing agent. Wraps `showroom:verify-content` and adds Publishing House-specific
spec alignment checks. Reviews content against Red Hat quality standards and the approved
project spec. Produces review reports and offers interactive fix loops.

### /rhdp-publishing-house:automation

Automation agent. Four sub-phases:

- **7a: Automation Requirements** — analyzes content to produce a reviewable automation manifest
  describing what needs to be pre-configured in the environment
- **7b: Catalog Item** — wraps `agnosticv:catalog-builder` and `agnosticv:validator` to create
  and validate AgnosticV catalog configuration (`rhdp_published` only; skipped for `self_published`)
- **7c: Automation Code** — writes Ansible collections or GitOps repos (Helm + ArgoCD) from
  the approved requirements, runs a safety check and catalog re-validation
- **7d: Testing** — human gate: deploy to a dev environment and verify automation works

Approach is constrained by deployment mode: `self_published` projects use GitOps only;
`rhdp_published` projects choose Ansible, GitOps, or both.

### /rhdp-publishing-house:worklog

Session bridging and human context. Manages `publishing-house/worklog.yaml` — decisions pending,
handoff notes, action items, session summaries. Not a task tracker; the manifest handles that.

- `"leave a note about X"` — expands and records a worklog entry
- `"what's outstanding"` — shows open items grouped by type
- `"resolve item X"` — marks an entry resolved
- `"session summary"` — writes a summary entry for the session

### /rhdp-publishing-house:security *(not yet implemented)*
### /rhdp-publishing-house:review *(not yet implemented)*

## Deployment Modes

Set during intake. Determines the automation path and publishing target.

| Mode | Automation | AgnosticV Catalog | Published In RHDP |
|------|------------|-------------------|-------------------|
| `rhdp_published` | Ansible, GitOps, or both | Required | Yes |
| `self_published` | GitOps only | Skipped | No — uses Field Source CI |

## Portal

The [RHDP Publishing House Portal](https://github.com/rhpds/rhdp-publishing-house-portal)
provides cross-project visibility for managers and PMs. Register projects by repo URL and see
all content flowing through the pipeline — kanban board, project table, phase detail, worklog
timeline, and launch instructions.

See [docs/portal.md](docs/portal.md).

## Getting Started

See [docs/getting-started.md](docs/getting-started.md).

## Autonomy Levels

| Level | Behavior |
|-------|----------|
| **supervised** (default) | Review every artifact before commit |
| **semi** | Review at phase gates only |
| **full** | Review at phase completion |

## Content Lifecycle

```
Intake → Vetting → Spec Refinement → [Approval] → Writing → Automation
  → Editing → Code & Security Review → Final Review → Ready for Publishing
```

Required phases: Intake, Approval, Editing, Code & Security Review, Final Review.
Optional: Vetting, Spec Refinement, Writing, Automation.
