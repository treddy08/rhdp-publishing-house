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

Automation agent. Two sub-phases:
- **7a: Catalog** — Wraps `agnosticv:catalog-builder` and `agnosticv:validator` to create
  and validate AgnosticV catalog configuration from the project spec.
- **7b: Environment** — Writes Ansible roles/playbooks or Argo+Helm manifests for environment
  setup, then runs its own code review cycle via `code-review:code-review`.

Only runs when `needs_automation: true` in the manifest. Uses Opus 4.6.

### /rhdp-publishing-house:security *(Phase 4)*
### /rhdp-publishing-house:review *(Phase 4)*

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
  → Automation → Security Review → Final Review → Ready for Publishing
```
