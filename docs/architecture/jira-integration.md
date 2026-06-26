# Jira Integration

## The Problem

Content development progress is invisible to leadership. During Summit 2026, we had checkpoints where projects were supposed to be at a certain percentage — but we had no data to assess that and no way to make cut decisions. Developers track everything in git-based manifests, which is great for the work but useless for management reporting.

Jira integration bridges this gap. The Publishing House (PH) system that manages content development automatically creates and updates Jira tickets as projects progress. No developer has to remember to update Jira — it happens as a side effect of doing the work.

## Current State

The RHDPCD Jira project is live and active, using the OJA-ITS-003 issue type scheme. A personal API token is used for dev environments; service account provisioning is pending for production.

## How It Works

### Four-Level Hierarchy

Everything maps to standard Jira issue types and their built-in hierarchy levels:

**Outcomes** are organizational groupings — broad categories that organize the team's work. Examples: "All Events", "Non-Event Content", "Architecture & Infrastructure". Manually created in Jira.

**Initiatives** are events or efforts — each event, program, or work stream gets one Initiative. Examples: Summit 2027, RH1, BAU Content Dev, Arcade Development. Each Initiative can have a due date for event-driven work (content freeze deadlines) or remain open-ended for ongoing work. Manually created in Jira.

**Epics** are projects — each content project (lab, workshop, demo) gets one Epic. PH auto-creates it at registration time. Lives under its parent Initiative if one is set.

**Tasks** are deliverables — each piece of work within a project gets a Task with story points. PH auto-creates tasks progressively as the project advances through gates.

```
Outcome: "All Events"
  └── Initiative: "Summit 2027 Labs"
        └── Epic: "OCP Getting Started Workshop"
              ├── Intake & Spec                    [13 pts] ✓ Done
              ├── Module 1: Content                [5 pts]  ✓ Done
              ├── Module 1: Automation             [8 pts]  ● In Progress
              ├── Module 1: Verified               [5 pts]  ○ To Do
              ├── Module 2: Content                [5 pts]  ● In Progress
              ├── Module 2: Automation             [8 pts]  ○ To Do
              ├── Module 2: Verified               [5 pts]  ○ To Do
              ├── Code Review                      [3 pts]  ○ To Do
              ├── Security Review                  [3 pts]  ○ To Do
              ├── E2E Test                         [8 pts]  ○ To Do
              └── Final Review                     [1 pt]   ○ To Do
```

### Progressive Task Creation

Jira tickets are not created all at once. They are created in two phases, matching the points where PH has enough information to define them.

**Phase 1 — At `ph_register`:** When a project is first registered with Central, PH creates:

- **Epic** for the project, parented under the Initiative if one is set in the manifest.
- **Intake & Spec task** (13 story points) covering spec development, vetting, and approval.
- **Assignee** resolved from the manifest's `owner_email` via Jira user search.

At this point, the module list is not finalized (it can change during spec refinement), so per-module tasks are not yet created.

**Phase 2 — At approval gate:** When the spec is frozen and the approval gate passes, PH creates the full set of per-module and review tasks:

- **Per-module tasks** for each non-supporting module:
    - `MODULE_CONTENT` (5 pts) — the actual instructional content
    - `MODULE_AUTOMATION` (8 pts) — infrastructure automation code
    - `MODULE_VERIFIED` (5 pts) — end-to-end test for that module
- **Cross-cutting review tasks:**
    - `CODE_REVIEW` (3 pts)
    - `SECURITY_REVIEW` (3 pts)
    - `E2E_TEST` (8 pts)
    - `FINAL_REVIEW` (1 pt)
- **Epic summary** updated to the finalized project name.

#### Supporting Page Exclusion

Intro, conclusion, overview, and summary modules are excluded from per-module Jira task creation. These are detected by title (case-insensitive match for "introduction", "conclusion", "overview", "summary") or by ID patterns like `-00-` or `-99-` in the module identifier. Supporting pages are part of the content but don't represent independent development effort — they're boilerplate or wrapper modules that don't need individual tracking.

### Points = Estimated Effort

Every deliverable gets a fixed point value based on its type. Points represent relative effort — not hours or days, but "how much work is this compared to other deliverables."

| Deliverable | Points | What It Represents |
|---|---|---|
| Intake & Spec | 13 | Spec development, RCARS vetting, approval |
| Module Content (each) | 5 | The actual instructional content (AsciiDoc) |
| Module Automation (each) | 8 | Infrastructure automation code for each module |
| Module Verified (each) | 5 | End-to-end test — content + automation work together |
| Code Review | 3 | Cross-cutting review of all code |
| Security Review | 3 | Security-focused review of code and config |
| E2E Test | 8 | Full end-to-end validation of the complete lab |
| Final Review | 1 | Stakeholder sign-off |

A 5-module workshop totals **118 points** (13 + 5x18 + 15). A 2-module quick lab totals **64 points**. The module count drives project size naturally.

Points are defaults. A manager can adjust them in Jira if a particular module is unusually complex or simple — for example, bumping a module's Automation from 8 to 13 if it involves complex operator configuration. PH won't overwrite manually adjusted values.

### Automatic Status Updates

PH updates Jira as work progresses — no one has to remember to do it. When a developer finishes writing Module 3's content, the corresponding Jira task moves to Done. When automation starts on Module 2, the task moves to In Progress.

Three sync paths ensure Jira stays current:

1. **Real-time during active development.** When a developer works in PH, every manifest update syncs to the Central backend, which immediately updates Jira.
2. **Periodic polling.** A background job checks project repos every 15-30 minutes for manifest changes made outside PH (manual edits, CI pipelines). Catches anything the real-time path missed.
3. **Manual refresh.** A "Sync now" button in the Central dashboard for on-demand sync.

### Sync Behavior

Sync is designed to be idempotent and self-healing:

- **Creates missing tasks.** If a new module is added to the manifest after approval, sync creates the corresponding MODULE_CONTENT, MODULE_AUTOMATION, and MODULE_VERIFIED tasks.
- **Closes orphaned tasks.** If a module is removed from the manifest, sync sets its tasks' story points to 0 and transitions them to Closed. The tasks are not deleted — they remain for audit trail.
- **Diffs and transitions status.** Sync compares the manifest's phase/module status with the Jira task status and transitions tasks to match (To Do, In Progress, Done).
- **Detects externally-deleted tasks.** If someone deletes a Jira task that PH created, sync detects the missing task and recreates it with the correct status and points.

### What You Can See

**Organization view:** Open the Jira dashboard. See all Outcomes with total points, completed points, and percentage done across all events and programs.

**Effort view:** Click an Outcome. See all Initiatives under it — each event or program — with per-effort progress. "Summit 2027 is at 62% with 3 weeks to go. RH1 is at 28%."

**Event view:** Click an Initiative. See all Epics under it with per-project progress. "OCP Getting Started is 85%. AI Observability is 40%."

**Project view:** Click an Epic. See every deliverable — which are done, which are in progress, which haven't started. Instantly see where a project is stuck. "Content is done on all modules but automation is behind on modules 3-5."

**Checkpoint decisions:** Due dates on Initiatives enable timeline views. Before a content freeze, you can see which projects are on track and which should be cut — based on actual point completion, not guesswork.

**Cross-cutting views:** Labels on Initiatives enable queries like "show me all event-driven work" or "how much BAU content are we producing this quarter."

## Who Does What

| Role | Jira Responsibility |
|------|---------------------|
| **Developers** | Nothing. PH handles Jira automatically. Developers can glance at their Epic if curious. |
| **Direct managers** | Create Initiatives for their events/efforts. Verify Jira reflects reality. Adjust points if defaults are wrong. Pull reports for their teams. |
| **PM** | Use Initiatives and Outcomes for portfolio tracking. Set due dates on Initiatives. Build dashboards for cross-effort views. |
| **Senior director** | Create Outcomes for organizational groupings. Consume dashboards. Drill into Initiatives and Epics. Make checkpoint/cut decisions based on point data. |

## What Jira Does NOT Track

- **How developers work.** PH session logs, worklog entries, and internal decision-making stay in PH. Jira shows what's done, not how it got done.
- **Express mode projects.** Express environments are disposable one-offs — no Jira tracking. Only projects going through the full content pipeline (onboarded or self-published) appear in Jira.
- **Implementation details of automation.** Whether automation is lab-wide or per-module is a developer concern. Jira tracks "is the automation for this module working," not how it's structured.