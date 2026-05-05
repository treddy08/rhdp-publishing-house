# Jira Integration Design Spec

**Date:** 2026-05-05
**Status:** Draft
**Phase:** 3 (Milestone 2 Roadmap)
**Depends on:** Phase 1 (RCARS MCP Gateway) — complete

## Problem

Management needs visibility into content development progress across the team. Today there is no structured way for a senior director to answer "how much Summit content is done" or "which projects are behind" without asking individual developers. During Summit 2026 lab development, checkpoints existed but there was no data to assess whether projects should be cut. PH tracks everything in git manifests — useful for developers, invisible to leadership.

## Audience

Three tiers with different needs and tool preferences:

| Tier | Primary Tool | What They Need |
|------|-------------|----------------|
| Content developers | PH (80%) / Jira (20%) | Don't want to think about Jira. It should just work. |
| Direct managers | Jira (50%) / Portal (50%) | Area-level status, verify Jira is current, generate reports |
| Senior director + PM | Jira (80%) / Portal (20%) | Portfolio view, effort-level rollups, points, checkpoints, cut decisions |

## Design Principles

1. **Manifest is the source of truth.** Jira is a one-directional sync target. PH → Jira always. Jira → PH never (v1).
2. **Only the Portal backend talks to Jira.** No LLM creates or modifies Jira tickets. No Jira credentials leave the Portal.
3. **Developers never need to touch Jira.** PH automates all Jira ticket creation and status updates.
4. **Managers own the strategic layer.** Initiatives (efforts) are created manually by managers. PH owns everything below that.
5. **Points are defaults, not mandates.** PH sets fixed point values at creation. Humans adjust in Jira. PH never overwrites point values.

---

## Jira Project

**Key:** RHDPPH (placeholder — final name TBD)
**Type:** Jira Cloud, Team-managed or Company-managed (TBD based on admin access)
**Site:** redhat.atlassian.net

### Why a Dedicated Project

GPTEINFRA (the existing RHDP Jira project) has 70+ issue types and shared schemes across all of RHDP. Adding custom workflows, fields, or automation rules for content tracking would affect unrelated work. A dedicated project provides:

- Custom workflow matching PH lifecycle phases without affecting GPTEINFRA
- Story points enabled on the right issue types by default
- Automation rules scoped to content work only
- Clean JQL: `project = RHDPPH` = all PH content work, no filtering needed

**Cross-project reporting still works.** Jira Cloud dashboards use JQL that spans projects. Issue links connect RHDPPH Epics to GPTEINFRA Initiatives. A single dashboard can show both infra and content work side by side.

### Issue Types Required

| Type | Hierarchy Level | Purpose |
|------|----------------|---------|
| Initiative | 2 | Effort grouping (Summit 2027, RH1, BAU) |
| Epic | 1 | One per PH project |
| Task | 0 | One per deliverable (with story points) |

### Workflow

Simple three-state workflow on Tasks:

```
To Do → In Progress → Done
```

No additional states. PH phases map to these three states:
- `pending` → To Do
- `in_progress` → In Progress
- `completed` / `skipped` → Done

---

## Ticket Hierarchy

```
Initiative (effort)            → "Summit 2027 Labs"           [manual, manager-created]
  └── Epic (project)           → "OCP Getting Started"        [auto, PH-created]
        ├── Design Doc          → 3 pts                       [auto]
        ├── Module 1: Outline   → 5 pts                       [auto]
        ├── Module 1: Content   → 5 pts                       [auto]
        ├── Module 1: Automation → 8 pts                      [auto]
        ├── Module 1: Verified  → 5 pts                       [auto]
        ├── Module 2: Outline   → 5 pts                       [auto]
        ├── Module 2: Content   → 5 pts                       [auto]
        ├── Module 2: Automation → 8 pts                      [auto]
        ├── Module 2: Verified  → 5 pts                       [auto]
        ├── ...
        ├── Code & Security Review → 3 pts                    [auto]
        ├── E2E Test            → 8 pts                       [auto]
        └── Final Review        → 1 pt                        [auto]
```

Each PH project = one Epic. One parent Initiative. One effort label.

---

## Points Model

Points represent relative effort. Fixed defaults set by PH at task creation. Managers adjust in Jira if needed — PH never overwrites point values on existing tasks.

### Deliverable Types and Default Points

| Deliverable | Points | Manifest Source | Count |
|---|---|---|---|
| Design Doc | 3 | `lifecycle.phases.intake.status` + `lifecycle.phases.vetting.status` | 1 per project |
| Module X: Outline | 5 | `lifecycle.phases.spec_refinement.modules[id=X].status` (NEW) | per module |
| Module X: Content | 5 | `lifecycle.phases.writing.modules[id=X].status` | per module |
| Module X: Automation | 8 | `lifecycle.phases.automation.modules[id=X].status` (NEW) | per module |
| Module X: Verified | 5 | `lifecycle.phases.writing.modules[id=X].verified` (NEW) | per module |
| Code & Security Review | 3 | `lifecycle.phases.code_security_review.status` | 1 per project |
| E2E Test | 8 | `lifecycle.phases.e2e_test.status` (NEW) | 1 per project |
| Final Review | 1 | `lifecycle.phases.final_review.status` | 1 per project |

**Manifest evolution notes:**
- **Design Doc** combines intake + vetting. Vetting is not its own Jira task — it's part of getting the spec right. Design Doc task moves to Done when intake is complete and vetting is either complete or skipped.
- **Module Outline** requires per-module status tracking under `spec_refinement`. Today `spec_refinement` is a single phase status. Manifest needs a `modules` array mirroring the writing phase structure.
- **Module Automation** requires per-module status tracking under `automation`. Today automation has `substeps` (requirements, catalog_item, automation_code, testing) but not per-module status. Manifest needs a `modules` array here too. This is a significant manifest evolution that aligns with the direction of per-module self-contained automation.
- Fields marked (NEW) require manifest additions — see Manifest Changes section.

### Example Project Sizes

| Project Type | Calculation | Total Points |
|---|---|---|
| 5-module workshop | 3 + 5×(5+5+8+5) + 3 + 8 + 1 | 130 |
| 3-module workshop | 3 + 3×(5+5+8+5) + 3 + 8 + 1 | 84 |
| 2-module quick lab | 3 + 2×(5+5+8+5) + 3 + 8 + 1 | 61 |

### Skipped Phases

When a developer skips a phase, PH transitions the corresponding Task to Done with 0 points. The project total shrinks accordingly, and percentage calculations stay accurate.

### Module Content + Automation Relationship

Content and Automation for a module are separate tasks with independent status, but the module is not truly complete until both are done AND the Verified task passes. The Verified task represents walking through the module end-to-end — testing content against live automation, finding problems, fixing both, re-testing until it works.

If automation is structured lab-wide (not per-module), each module's Automation task stays open until the relevant automation for that module is working. They may all complete together — that's fine. Jira reflects "is the automation for this module's exercises working," not "is there a per-module Ansible role."

### Regression Handling

If a change to automation or content affects a previously verified module, the Verified task should be reopened. This is a future PH feature (backlogged): PH detects that a commit touches files affecting completed modules and reopens the Verified tasks so they can be re-tested. For v1, manual reopening by the developer or manager.

---

## Effort Categories & Initiative Management

### What an Initiative Represents

A business-level grouping of content work. Answers: "What are we working toward and by when?"

Examples:
- "Summit 2027 Labs"
- "RH1 FY27 Content"
- "BAU Content Development"
- "Summit Connect 2027"
- "Blog Series: AI on OpenShift"
- "Architecture Development"
- "Arcade Development"

### Initiative Lifecycle

**Created by:** Managers or PM, manually in Jira. PH never creates Initiatives.

**Key fields:**

| Field | Purpose | Example |
|---|---|---|
| Summary | Effort name | "Summit 2027 Labs" |
| Description | Scope, goals, deadline context | "All labs for Summit 2027. Content freeze: 2027-04-15." |
| Due date | Hard deadline (event-driven) or empty (BAU) | 2027-04-15 |
| Labels | Broad effort type for cross-cutting queries | `event`, `bau`, `blog`, `architecture`, `arcade` |

### Project-to-Initiative Assignment

During intake, PH queries the Portal for open Initiatives in RHDPPH. Developer selects one or "None — unassigned." The Epic is created as a child of the selected Initiative with a matching label.

Unassigned Epics can be moved under an Initiative later by a manager in Jira. Single parent per Epic — no multi-effort linking needed. If a project changes efforts (rare), someone drags the Epic in Jira.

### Senior Director's View

| Level | What They See | Jira Action |
|---|---|---|
| Portfolio | All Initiatives with total/completed points, % done, due dates | Dashboard |
| Effort | All Epics under one Initiative with per-project points | Click Initiative |
| Project | All Tasks under one Epic with per-deliverable status | Click Epic |
| Cross-cutting | All work by effort type (all events, all BAU) | Label-based JQL filter |

---

## Integration Architecture

### Auth

| Component | Value |
|---|---|
| Auth method | Jira API token (Basic auth: `email:token`) |
| Account | Dedicated Jira service account (not personal) |
| Secret storage | K8s Secret `ph-jira-credentials` in `publishing-house-dev` |
| Secret management | Ansible deployer |
| API version | Jira Cloud REST API v3 |

**MAJOR TODO:** Determine if Red Hat can provision a Jira Cloud service account on redhat.atlassian.net. If not, evaluate alternatives (shared team token, OAuth 2.0 app). This is a gating dependency for deployment — must be resolved before implementation begins.

### Portal Backend: JiraSyncService

Single integration class. Pure Python, deterministic, no LLM in the loop.

```
app/services/jira_sync.py

JiraSyncService
  ├── create_project(manifest, initiative_key) → epic_key + task_keys
  ├── sync_project(manifest, task_mapping) → list of changes made
  ├── get_open_initiatives() → list of initiatives (cached, 15min TTL)
  └── _diff_state(manifest, jira_state) → list of transitions needed
```

**`create_project`:** Reads manifest, counts modules, creates Epic + all Tasks in one Jira API batch. Returns Jira keys stored in Portal DB.

**`sync_project`:** Compares manifest phase statuses against Jira task statuses via the task mapping table. Transitions tasks that are out of sync. Adds a comment to the Epic summarizing changes. Idempotent — same manifest state produces no changes.

**`get_open_initiatives`:** Queries Jira for open Initiatives in RHDPPH. Cached in Portal DB, refreshed every 15 minutes or on-demand.

**`_diff_state`:** Compares manifest state against Jira state, returns list of transitions needed. Uses the task mapping table to know which Jira issue corresponds to which manifest path.

### Task Mapping Table (Portal DB)

```
jira_task_mappings
  ├── id (PK)
  ├── project_id (FK → projects)
  ├── jira_epic_key (e.g., "RHDPPH-42")
  ├── deliverable_type (enum: design_doc, module_outline, module_content,
  │                     module_automation, module_verified, code_review,
  │                     e2e_test, final_review)
  ├── module_id (nullable — null for project-level tasks)
  ├── jira_issue_key (e.g., "RHDPPH-87")
  ├── manifest_path (e.g., "lifecycle.phases.writing.modules[id=module-03].status")
  ├── default_points (int)
  ├── created_at
  └── updated_at
```

Every row maps one manifest path to one Jira issue. The sync service reads this table to know what to diff and what to transition.

### Sync Triggers

Three paths, all converging on the Portal backend:

**1. MCP-triggered (real-time, during active CC work)**

```
CC session → manifest update → ph_sync_manifest MCP tool → Portal receives manifest
  → Portal detects state change → JiraSyncService.sync_project() → Jira updated
```

For new projects (no Jira mapping exists), the Portal calls `create_project()` instead.

**2. Polling (near-real-time, catches manual edits)**

Portal background job (APScheduler) runs every 15-30 minutes:
- Scans known project repos for manifest changes (compare hash against last-known)
- If changed, pulls updated manifest, runs `sync_project()`
- Catches changes made outside CC (manual git edits, CI pipelines, other tools)

**3. Manual refresh (on-demand)**

- Portal UI: "Sync now" button on project detail page
- MCP tool: `ph_jira_sync` (read-only trigger — tells Portal to sync, doesn't call Jira directly)

### Error Handling

| Scenario | Behavior |
|---|---|
| Jira API down | Log error, skip sync, reconciliation job catches it on next run |
| Jira task deleted manually | Log warning, recreate task, update mapping table |
| Manifest has module with no Jira task | Create missing task, add to mapping table |
| Module removed from manifest | Transition task to Done with 0 points, comment "Module removed" |
| API rate limit | Exponential backoff, reconciliation catches remainder |
| Service account token expired | Health endpoint reports Jira unhealthy, alert via monitoring |

### What the Portal Exposes via MCP (Read-Only)

| Tool | Purpose | Data Source |
|---|---|---|
| `ph_jira_status` | Show Jira status of current project | Portal DB (no Jira API call) |
| `ph_jira_link` | Return Jira Epic URL | Portal DB |

These are convenience tools for CC users. No write operations. No Jira credentials exposed.

### Atlassian MCP Server Relationship

The Atlassian MCP server configured in Claude Code is for interactive human use (querying Jira, browsing issues). The Portal backend does NOT use it — it calls the Jira REST API directly via `httpx`. These are independent integration paths that coexist without conflict.

---

## Manifest Changes

### New fields in `integrations`:

```yaml
integrations:
  jira:
    epic_key: "RHDPPH-42"
    initiative_key: "RHDPPH-10"
    effort_label: "summit-2027"
    synced_at: "2026-05-05T14:30:00Z"
```

### Per-module outline tracking (new structure under spec_refinement):

```yaml
spec_refinement:
  status: completed
  completed_at: "2026-04-10"
  modules:                          # NEW — per-module outline status
    - id: "module-01"
      title: "Your First Application"
      status: completed             # pending / in_progress / completed
    - id: "module-02"
      title: "Expanding Your Deployment"
      status: completed
```

### Per-module automation tracking (new structure under automation):

```yaml
automation:
  status: in_progress
  needs_automation: true
  substeps:                          # existing — kept for backward compat
    requirements: completed
    catalog_item: completed
    automation_code: in_progress
    testing: pending
  modules:                           # NEW — per-module automation status
    - id: "module-01"
      status: completed
    - id: "module-02"
      status: in_progress
```

### New per-module verification fields (under writing):

```yaml
writing:
  modules:
    - id: "module-01"
      title: "Your First Application"
      status: drafted
      content_path: "..."
      verified: false                # NEW — has this module passed testing?
      verified_at: null              # NEW — when was it verified?
```

### New phase:

```yaml
e2e_test:
  status: pending                    # pending / in_progress / completed / failed
  completed_at: null
  results: null                      # summary of test results
```

### Template update

Manifest template (`template/publishing-house/manifest.yaml`) updated with all new fields. Existing pre-Jira projects work without changes — sync service treats missing fields as "not yet started" and creates Jira tasks in To Do status.

### Backward compatibility

The sync service handles manifests with and without the new fields:
- Missing `integrations.jira` → project has no Jira mapping yet, eligible for creation
- Missing `spec_refinement.modules` → outline status derived from phase-level `spec_refinement.status` (all outlines share one status)
- Missing `automation.modules` → automation status derived from phase-level `automation.status`
- Missing `writing.modules[].verified` → treated as `false`
- Missing `e2e_test` → treated as `pending`

---

## Out of Scope (v1)

| Feature | Why Deferred |
|---|---|
| Jira → PH write-back | Conflict resolution is complex. One-directional sync first. v2 feature. |
| Manager reopens task in Jira → PH respects it | Requires bidirectional awareness. v2. |
| Automated regression detection (reopen Verified tasks) | PH feature, not Jira feature. Backlogged. |
| Jira webhooks to Portal | Per-repo webhook setup doesn't scale. Polling + MCP trigger sufficient. |
| Express project tracking in Jira | Express is transient — no Jira presence by design. |
| Self-service API key onboarding for CC users | Important but separate from Jira integration. Backlogged. |

---

## Prerequisites

| Prerequisite | Status | Blocker? |
|---|---|---|
| RHDPPH Jira project created | Not started | Yes — need project admin approval |
| Jira service account provisioned | Not started | Yes — gating dependency for deployment |
| Initiative issue type available in RHDPPH | Not started | Yes — needed for hierarchy |
| Phase 1 (MCP Gateway) | Complete | No |
| Phase 2 (Express Mode Framework) | Complete | No |

---

## Backlog Items Identified During Design

| Item | Description | Where |
|---|---|---|
| Regression detection | PH detects changes affecting completed modules, reopens Verified tasks | PH backlog |
| CC user onboarding flow | Self-service or scripted API key generation and distribution | PH backlog |
| Chatbot supports all modes | Chatbot is for onboarded, self-published, AND express — not just express | Chatbot phase (Phase 4) |
| Jira → PH write-back (v2) | Manager annotations flowing from Jira to PH, scoped to specific fields | JIRA-F-01 in REQUIREMENTS.md |
