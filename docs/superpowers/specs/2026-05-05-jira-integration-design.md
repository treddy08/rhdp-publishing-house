# Jira Integration Design Spec

**Date:** 2026-05-05
**Status:** Draft
**Phase:** 3 (Milestone 2 Roadmap)
**Depends on:** Phase 1 (RCARS MCP Gateway) — complete, Publishing House Central architecture — complete (2026-06-19 spec)

## Problem

Management needs visibility into content development progress across the team. Today there is no structured way for a senior director to answer "how much Summit content is done" or "which projects are behind" without asking individual developers. During Summit 2026 lab development, checkpoints existed but there was no data to assess whether projects should be cut. PH tracks everything in git manifests — useful for developers, invisible to leadership.

## Audience

Three tiers with different needs and tool preferences:

| Tier | Primary Tool | What They Need |
|------|-------------|----------------|
| Content developers | PH (80%) / Jira (20%) | Don't want to think about Jira. It should just work. |
| Direct managers | Jira (50%) / Central (50%) | Area-level status, verify Jira is current, generate reports |
| Senior director + PM | Jira (80%) / Central (20%) | Portfolio view, effort-level rollups, points, checkpoints, cut decisions |

## Design Principles

1. **Manifest is the source of truth.** Jira is a one-directional sync target. PH → Jira always. Jira → PH never (v1).
2. **Onboarded projects only.** Jira integration applies to `rhdp_published` (onboarded) projects. Self-published and express projects are not tracked in Jira — self-published work is done by others on their own schedule, and express is transient.
3. **Only the Central backend talks to Jira.** No LLM creates or modifies Jira tickets. No Jira credentials leave Central.
4. **Developers never need to touch Jira.** PH automates all Jira ticket creation and status updates.
5. **Managers own the strategic layer.** Initiatives (efforts) are created manually by managers. PH owns everything below that.
6. **Points are defaults, not mandates.** PH sets fixed point values at creation. Humans adjust in Jira. PH never overwrites point values.

---

## Jira Project

**Key:** RHDPCD (RHDP Content Development)
**Template:** Template 2 — Basic Project (non-PGE)
**Site:** redhat.atlassian.net (Jira Cloud)

**Post-creation scheme change:** Template 2 defaults to OJA-ITS-001 (Bare Bones: Story, Sub-Task only). After project creation, use Delegated Project Admin to switch to **OJA-ITS-003 (Standard)** which provides Initiative, Epic, Task — the three-level hierarchy PH needs. This is a self-service change, no PME ticket required. See [How do Project Admins align with Red Hat Standards in Jira?](https://redhat.atlassian.net/wiki/spaces/HUB/pages/190190555) and [Adopting Approved Work Types](https://redhat.atlassian.net/wiki/spaces/HUB/pages/190190124).

**Scheme reference:** [OJA: Jira Configuration Taxonomy](https://redhat.atlassian.net/wiki/spaces/HUB/pages/190189089) and [Requesting a new Jira project](https://redhat.atlassian.net/servicedesk/customer/portal/67/article/421568311).

### Why a Dedicated Project

GPTEINFRA (the existing RHDP Jira project) has 70+ issue types and shared schemes across all of RHDP. Adding custom workflows, fields, or automation rules for content tracking would affect unrelated work. A dedicated project provides:

- Custom workflow matching PH lifecycle phases without affecting GPTEINFRA
- Story points enabled on the right issue types by default
- Automation rules scoped to content work only
- Clean JQL: `project = RHDPCD` = all PH content work, no filtering needed

**Cross-project reporting still works.** Jira Cloud dashboards use JQL that spans projects. Issue links connect RHDPCD Epics to GPTEINFRA Initiatives. A single dashboard can show both infra and content work side by side.

### Issue Types Required

| Type | Hierarchy Level | ID | Purpose |
|------|----------------|-----|---------|
| Outcome | 3 | 10130 | Organizational grouping ("All Events", "Non-Event Content") |
| Initiative | 2 | 10103 | Effort grouping (Summit 2027, RH1, BAU) |
| Epic | 1 | 10000 | One per PH project |
| Task | 0 | 10014 | One per deliverable (with story points) |

OJA-ITS-003 also includes Story, Bug, Vulnerability, Weakness, and Sub-task. PH uses only the four types above.

### Workflow

OJA-ITS-003 provides a four-state workflow. All transitions are global (any state can reach any other state).

| Status | ID | Transition ID | Category | PH Maps To |
|--------|----|---------------|----------|------------|
| New | 10142 | 51 | To Do | `pending` |
| Refinement | 10143 | 61 | To Do | *(not used by PH)* |
| In Progress | 3 | 31 | In Progress | `in_progress` |
| Closed | 6 | 41 | Done | `completed` / `skipped` |

PH uses 3 of 4 states (skips Refinement). The Closed transition requires a resolution field (e.g., "Done").

### Key Custom Fields

| Field | ID | Available On | Purpose |
|-------|-----|-------------|---------|
| Story Points | customfield_10028 | Task, Story, Initiative | Effort estimation (float) |
| Epic Link | customfield_10014 | Task, Story | Parent Epic linking |
| Epic Name | customfield_10011 | Epic | Display name |

---

## Ticket Hierarchy

```
Outcome (organizational)       → "All Events", "Non-Event Content"  [manual, director-created]
  └── Initiative (effort)      → "Summit 2027 Labs"                 [manual, manager-created]
        └── Epic (project)     → "OCP Getting Started"              [auto, PH-created]
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

**Project identity = repo URL + branch** (per Central architecture). A feature branch of the same repo gets its own Epic and independent phase progression. The Jira task mapping table uses `project_id` (which encodes repo URL + branch) as the foreign key, not repo URL alone.

Outcomes group Initiatives by broad organizational category. Directors create these;
managers place their Initiatives under the appropriate Outcome. PH does not create or
sync Outcomes — they're a portfolio-level construct managed by leadership.

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

### Phase Profiles and Task Creation

Central's `PhaseEngine` defines which phases exist per deployment mode (onboarded, self-published, express). Tasks are created based on the project's phase profile, not a universal hardcoded list. Different deployment modes may produce different task sets.

If a phase profile is extended later (e.g., E2E test added as a separate phase), new tasks are created for existing projects on next sync.

In rare cases where a manager decides to bypass a task in Jira (e.g., marking a task Done without the work being completed), the task transitions to Done with 0 points. The project total shrinks accordingly, and percentage calculations stay accurate. This is an exception path managed in Jira, not a PH workflow.

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

During intake, PH queries Central for open Initiatives in RHDPCD. Developer selects one or "None — unassigned." The Epic is created as a child of the selected Initiative with a matching label.

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

**Initial development uses a personal Jira account** (nstephan@redhat.com) with an API token stored in the Ansible vars (gitignored). This unblocks implementation while the service account is provisioned. The token and email are swappable — replace `jira_email` and `jira_api_token` in the env-specific vars file when the service account is ready.

**TODO for production:** Provision a dedicated Jira Cloud service account on redhat.atlassian.net. If not possible, evaluate alternatives (shared team token, OAuth 2.0 app). This remains a dependency for production deployment.

### Central Backend: JiraSyncService

Single integration class in `rhdp-publishing-house-central`. Pure Python, deterministic, no LLM in the loop.

```
app/services/jira_sync.py

JiraSyncService
  ├── create_project(manifest, initiative_key, phase_profile) → epic_key + task_keys
  ├── sync_project(manifest, task_mapping) → list of changes made
  ├── get_open_initiatives() → list of initiatives (cached, 15min TTL)
  └── _diff_state(manifest, jira_state) → list of transitions needed
```

**`create_project`:** Uses `PhaseEngine.get_profile(deployment_mode)` to determine which deliverable tasks to create for this project's deployment mode. Reads manifest, counts modules, creates Epic + all Tasks in one Jira API batch. Returns Jira keys stored in Central DB. Different deployment modes may produce different task sets.

**`sync_project`:** Compares manifest phase statuses against Jira task statuses via the task mapping table. Transitions tasks that are out of sync. Adds a comment to the Epic summarizing changes and linking to the custody chain gate decision that triggered the sync. Idempotent — same manifest state produces no changes.

**`get_open_initiatives`:** Queries Jira for open Initiatives in RHDPCD. Cached in Central DB, refreshed every 15 minutes or on-demand.

**`_diff_state`:** Compares manifest state against Jira state, returns list of transitions needed. Uses the task mapping table to know which Jira issue corresponds to which manifest path.

### Task Mapping Table (Central DB)

```
jira_task_mappings
  ├── id (PK)
  ├── project_id (FK → projects)
  ├── jira_epic_key (e.g., "RHDPCD-42")
  ├── deliverable_type (enum: design_doc, module_outline, module_content,
  │                     module_automation, module_verified, code_review,
  │                     e2e_test, final_review)
  ├── module_id (nullable — null for project-level tasks)
  ├── jira_issue_key (e.g., "RHDPCD-87")
  ├── manifest_path (e.g., "lifecycle.phases.writing.modules[id=module-03].status")
  ├── default_points (int)
  ├── created_at
  └── updated_at
```

Every row maps one manifest path to one Jira issue. The sync service reads this table to know what to diff and what to transition.

This table lives alongside Central's existing models: `Project` (with cached JSONB phase statuses), `GateRecord` (custody chain), and `SubmittedResult` (local skill outputs). The `project_id` FK references the `Project` model, which identifies projects by `repo_url + branch`.

### Sync Triggers

Three paths, all converging on the Central backend. Central reads project state from git via `GitRepoReader` (GitHub API, no full clone) — there is no `ph_sync_manifest` push model.

**1. Gate-driven (real-time, during active CC work)**

```
Skill completes phase work → pushes to git
  → calls ph_request_gate(repo_url, branch, target_phase)
    → Central reads manifest from git via GitRepoReader
      → Gate evaluates, records decision in custody chain
        → If state changed, JiraSyncService.sync_project() → Jira updated
```

For new projects (no Jira mapping exists), Central calls `create_project()` when the **approval gate** passes — the point where the spec is frozen and the module list is stable. Earlier gates (vetting, spec refinement) don't trigger Jira creation because modules may still change during the vetting ⇄ spec refinement loop.

Subsequent gate passes sync task statuses to Jira. This ensures Jira reflects validated progress, not work-in-progress.

**2. Periodic sync (near-real-time, catches drift)**

Central's existing APScheduler periodic sync already reads manifests from git via `GitRepoReader` to update cached phase statuses. The Jira sync hooks into this: after updating cached statuses, compare against Jira state via the task mapping table. If out of sync, run `JiraSyncService.sync_project()`.

This catches changes made outside gate calls: manual git edits, CI pipeline updates, and any state drift between Central and Jira.

**3. Dashboard-triggered (on-demand)**

Central dashboard: "Sync to Jira" button on project detail page. Calls `JiraSyncService.sync_project()` directly. No separate MCP tool needed — this is a dashboard-only action, consistent with Central's minimal MCP tool surface.

### Error Handling

| Scenario | Behavior |
|---|---|
| Jira API down | Log error, skip sync, reconciliation job catches it on next run |
| Jira task deleted manually | Log warning, recreate task, update mapping table |
| Manifest has module with no Jira task | Create missing task, add to mapping table |
| Module removed from manifest | Transition task to Done with 0 points, comment "Module removed" |
| API rate limit | Exponential backoff, reconciliation catches remainder |
| Service account token expired | Health endpoint reports Jira unhealthy, alert via monitoring |

### Jira Data in MCP Responses

No separate Jira MCP tools. Jira metadata is folded into the existing `ph_get_status` response, consistent with Central's minimal MCP tool surface (7 high-level tools):

```json
{
  "...existing ph_get_status fields...",
  "jira": {
    "epic_key": "RHDPCD-42",
    "epic_url": "https://redhat.atlassian.net/browse/RHDPCD-42",
    "initiative_key": "RHDPCD-10",
    "points_completed": 45,
    "points_total": 130,
    "synced_at": "2026-07-15T14:30:00Z"
  }
}
```

The `jira` block is `null` for projects not yet linked to Jira (e.g., express mode projects). Skills present this data conversationally — one fewer MCP tool call per status check.

### Custody Chain Integration

When a gate passes and triggers a Jira sync, `JiraSyncService` adds a comment to the Jira Epic summarizing the gate decision:

- Phase name, result (approved/rejected/overridden), who requested, who approved
- Override decisions are flagged: "Proceeded despite high overlap — override recorded in custody chain"
- Comments are human-readable, not machine-cross-references — managers get a partial audit trail in Jira without needing to check the Central dashboard for every decision
- Gate IDs from the custody chain are not exposed in Jira

This ensures that the Jira Epic comment history tells the story of how the project progressed, including any exceptions.

### Atlassian MCP Server Relationship

The Atlassian MCP server configured in Claude Code is for interactive human use (querying Jira, browsing issues). Central's `JiraSyncService` calls the Jira REST API directly via `httpx`. These are independent integration paths that coexist without conflict.

---

## Manifest Changes

### New fields in `integrations`:

```yaml
integrations:
  jira:
    epic_key: "RHDPCD-42"
    initiative_key: "RHDPCD-10"
    effort_label: "summit-2027"
    synced_at: "2026-05-05T14:30:00Z"
```

### Developer option: disabling Jira sync

Not included in the manifest template. Developers who need to test the PH pipeline repeatedly without creating Jira issues can add this to their project manifest:

```yaml
integrations:
  jira:
    enabled: false
```

When `enabled` is `false`, Central skips all Jira operations (creation, sync, comments) for that project. Defaults to `true` when omitted. This is a per-project setting — it doesn't affect other projects or the Central configuration.

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
| Jira webhooks to Central | Per-repo webhook setup doesn't scale. Gate-driven sync + periodic reconciliation sufficient. |
| Express project tracking in Jira | Express is transient — no Jira presence by design. |
| Self-published project tracking in Jira | Self-published work is done by others on their own schedule. Not useful for portfolio tracking in v1. Can add later if needed. |
| Self-service API key onboarding for CC users | Important but separate from Jira integration. Backlogged. |

---

## Prerequisites

| Prerequisite | Status | Blocker? |
|---|---|---|
| RHDPCD Jira project created | **Complete** (2026-06-18) | No |
| Switch to OJA-ITS-003 (Standard) | **Complete** (2026-06-22, verified via API) | No |
| Jira service account provisioned | Not started (personal account used for dev) | Yes — gating dependency for **production** deployment |
| Phase 1 (MCP Gateway) | Complete | No |
| Publishing House Central architecture | **Complete** (2026-06-19 spec, implemented) | No |

---

## Backlog Items Identified During Design

| Item | Description | Where |
|---|---|---|
| Regression detection | PH detects changes affecting completed modules, reopens Verified tasks | PH backlog |
| CC user onboarding flow | Self-service or scripted API key generation and distribution | PH backlog |
| Chatbot supports all modes | Chatbot is for onboarded, self-published, AND express — not just express | Chatbot phase (Phase 4) |
| Jira → PH write-back (v2) | Manager annotations flowing from Jira to PH, scoped to specific fields | JIRA-F-01 in REQUIREMENTS.md |
