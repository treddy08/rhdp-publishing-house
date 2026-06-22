# Jira Integration

!!! success "Implemented"
    Designed 2026-05-05, implemented 2026-06-22. Deployed to central-dev. RHDPCD Jira project active with OJA-ITS-003 scheme. Using personal API token for dev; service account provisioning pending for production.

## The Problem

Content development progress is invisible to leadership. During Summit 2026, we had checkpoints where projects were supposed to be at a certain percentage — but we had no data to assess that and no way to make cut decisions. Developers track everything in git-based manifests, which is great for the work but useless for management reporting.

Jira integration bridges this gap. The Publishing House (PH) system that manages content development automatically creates and updates Jira tickets as projects progress. No developer has to remember to update Jira — it happens as a side effect of doing the work.

## How It Works

### Three-Level Hierarchy

Everything maps to standard Jira concepts:

**Initiatives** are efforts — Summit 2027, RH1, BAU Content Dev, Arcade Development, Blog Series, etc. Created by managers to represent what the team is working toward. Each Initiative can have a due date for event-driven work (content freeze deadlines) or remain open-ended for ongoing work.

**Epics** are projects — each content project (lab, workshop, demo) gets one Epic. Created automatically by Central when the approval gate passes (spec is frozen at that point). Lives under its parent Initiative.

**Tasks** are deliverables — each piece of work within a project gets a Task with story points. Created automatically by PH alongside the Epic.

```
Initiative: "Summit 2027 Labs"
  └── Epic: "OCP Getting Started Workshop"
        ├── Design Doc                    [3 pts]  ✓ Done
        ├── Module 1: Outline             [5 pts]  ✓ Done
        ├── Module 1: Content             [5 pts]  ✓ Done
        ├── Module 1: Automation          [8 pts]  ● In Progress
        ├── Module 1: Verified            [5 pts]  ○ To Do
        ├── Module 2: Outline             [5 pts]  ✓ Done
        ├── Module 2: Content             [5 pts]  ● In Progress
        ├── Module 2: Automation          [8 pts]  ○ To Do
        ├── Module 2: Verified            [5 pts]  ○ To Do
        ├── Code & Security Review        [3 pts]  ○ To Do
        ├── E2E Test                      [8 pts]  ○ To Do
        └── Final Review                  [1 pt]   ○ To Do
```

### Points = Estimated Effort

Every deliverable gets a fixed point value based on its type. Points represent relative effort — not hours or days, but "how much work is this compared to other deliverables."

| Deliverable | Points | What It Represents |
|---|---|---|
| Design Doc | 3 | Overall workshop design, audience, objectives |
| Module Outline (each) | 5 | Spec/contract for each module — critical to get right |
| Module Content (each) | 5 | The actual instructional content (AsciiDoc) |
| Module Automation (each) | 8 | Infrastructure automation code for each module |
| Module Verified (each) | 5 | End-to-end test — content + automation work together |
| Code & Security Review | 3 | Cross-cutting review of all code and content |
| E2E Test | 8 | Full end-to-end validation of the complete lab |
| Final Review | 1 | Stakeholder sign-off |

A 5-module workshop totals **130 points**. A 2-module quick lab totals **61 points**. The module count drives project size naturally.

Points are defaults. A manager can adjust them in Jira if a particular module is unusually complex or simple — for example, bumping a module's Automation from 8 to 13 if it involves complex operator configuration. PH won't overwrite manually adjusted values.

### Automatic Status Updates

PH updates Jira as work progresses — no one has to remember to do it. When a developer finishes writing Module 3's content, the corresponding Jira task moves to Done. When automation starts on Module 2, the task moves to In Progress.

Three sync paths ensure Jira stays current:

1. **Real-time during active development.** When a developer works in PH, every manifest update syncs to the Portal backend, which immediately updates Jira.
2. **Periodic polling.** A background job checks project repos every 15-30 minutes for manifest changes made outside PH (manual edits, CI pipelines). Catches anything the real-time path missed.
3. **Manual refresh.** A "Sync now" button in the Portal UI for on-demand sync.

### What You Can See

**Portfolio view:** Open the Jira dashboard. See all Initiatives with total points, completed points, and percentage done. "Summit 2027 is at 62% with 3 weeks to go. RH1 is at 28%."

**Effort view:** Click an Initiative. See all projects under it with per-project progress. "OCP Getting Started is 85%. AI Observability is 40%."

**Project view:** Click an Epic. See every deliverable — which are done, which are in progress, which haven't started. Instantly see where a project is stuck. "Content is done on all modules but automation is behind on modules 3-5."

**Checkpoint decisions:** Due dates on Initiatives enable timeline views. Before a content freeze, you can see which projects are on track and which should be cut — based on actual point completion, not guesswork.

**Cross-cutting views:** Labels on Initiatives enable queries like "show me all event-driven work" or "how much BAU content are we producing this quarter."

## Who Does What

| Role | Jira Responsibility |
|------|---------------------|
| **Developers** | Nothing. PH handles Jira automatically. Developers can glance at their Epic if curious. |
| **Direct managers** | Create Initiatives for their areas. Verify Jira reflects reality. Adjust points if defaults are wrong. Pull reports for their teams. |
| **PM** | Use Initiatives for portfolio tracking. Set due dates. Build dashboards for cross-effort views. |
| **Senior director** | Consume dashboards. Drill into Initiatives and Epics. Make checkpoint/cut decisions based on point data. |

## What Jira Does NOT Track

- **How developers work.** PH session logs, worklog entries, and internal decision-making stay in PH. Jira shows what's done, not how it got done.
- **Express mode projects.** Express environments are disposable one-offs — no Jira tracking. Only projects going through the full content pipeline (onboarded or self-published) appear in Jira.
- **Implementation details of automation.** Whether automation is lab-wide or per-module is a developer concern. Jira tracks "is the automation for this module working," not how it's structured.

## Prerequisites

Two things need to happen before this can go live:

1. **New Jira project.** We need a dedicated Jira project (working name: RHDPPH) so we can configure workflows, story points, and automation rules without affecting GPTEINFRA. Cross-project dashboards and issue links keep everything visible alongside existing RHDP work.

2. **Jira service account.** The Portal backend needs a service account with API access to create and update tickets programmatically. This is the integration identity — not tied to any individual's account.
