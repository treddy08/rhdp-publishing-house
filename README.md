# RHDP Publishing House

AI-powered content lifecycle management for Red Hat Demo Platform.

## Overview

One command — `/rhdp-publishing-house` — provides a persistent, state-aware orchestrator
that manages the entire content lifecycle through specialized AI agents. Content developers
become content architects: design the architecture, agents handle the writing, editing,
automation, and review.

## Skills

### /rhdp-publishing-house (orchestrator)

Entry point. Reads project manifest, presents current state, recommends next action,
dispatches agent skills. Supports three autonomy levels: supervised (default), semi, full.

### /rhdp-publishing-house:intake

Spec generation and RCARS vetting. Three intake paths:
- Full spec provided — agent fills gaps
- Rough idea — agent builds spec through conversation
- RCARS gap — gap description becomes seed for new spec

### /rhdp-publishing-house:writer

Content writing agent. Wraps `showroom:create-lab` (workshops) and `showroom:create-demo`
(demos) to generate Showroom AsciiDoc from approved module outlines. Works module-by-module.

### /rhdp-publishing-house:editor

Technical editing agent. Wraps `showroom:verify-content` and adds Publishing House-specific
spec alignment checks. Reviews content against Red Hat quality standards and the approved
project spec. Produces review reports and offers interactive fix loops.
### /rhdp-publishing-house:automation

Automation agent. Four sub-phases:
- **7a: Catalog Item** — Wraps `agnosticv:catalog-builder` and `agnosticv:validator` to create
  and validate AgnosticV catalog configuration.
- **7b: Automation Requirements** — Analyzes content to produce a reviewable automation manifest
  describing what needs to be pre-configured.
- **7c: Automation Code** — Writes Ansible collections or GitOps repos (Helm + ArgoCD) from
  the approved requirements, then runs its own code review cycle.
- **7d: Testing** — Human gate: deploy to a dev environment and verify automation works.
  Must be completed or explicitly skipped.
- **7e: E2E Checks** — End-to-end validation *(deferred)*.

Only runs when `needs_automation: true` in the manifest. Uses Opus 4.6.

### /rhdp-publishing-house:security *(not yet implemented)*
### /rhdp-publishing-house:review *(not yet implemented)*

## Portal

The [RHDP Publishing House Portal](https://github.com/rhpds/rhdp-publishing-house-portal) provides cross-project visibility for managers and PMs. Register projects by repo URL and see all content flowing through the pipeline — kanban board, project table, and phase-level detail with artifacts and dates.

See [docs/dashboard.md](docs/dashboard.md).

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
Intake → Vetting → Spec Refinement → [Approval] → Writing → Editing
  → Automation → Code & Security Review → Final Review → Ready for Publishing
```
