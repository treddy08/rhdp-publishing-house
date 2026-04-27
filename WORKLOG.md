# Publishing House — Development Worklog

Session notes and open items for the PH dev team.

---

## 2026-04-24

### Session Summary

Redesigned the orchestrator's project discovery and added phase-gate repo creation.
Reviewed and aligned all docs with the current state. Debugged and resolved a testing
issue where the local skills clone was stale — all skill changes were being pushed to the
remote but not pulled into the directory Claude Code was reading from.

### What Was Done

- **Orchestrator discovery redesign:** Replaced aggressive walk-up-from-CWD with CWD check first, then one-level subdirectory scan. When multiple projects found, lists them with a "None of these" option. When no project is found, presents three options: provide a local path, provide a remote git URL (any host) to clone, or create a new project from the template. Git pull deferred until after project is found.
- **Phase-gate repo creation:** Orchestrator now checks for Showroom and automation repos before dispatching to writer/automation skills. If repos don't exist, walks the user through creating them (manual steps first, `gh` CLI shortcut second), then handles `git submodule add`, manifest update, commit, and push. Skills never deal with repo setup — they receive ready-to-use directories.
- **Intake cleanup:** Removed repo setup from the intake skill — this responsibility moved to the orchestrator's pre-dispatch gates. Showroom repo is created before writing starts, automation repo before automation code (7c) starts.
- **Docs alignment:** Updated getting-started, how-it-works, executive-summary, README, skills-plugin README, and intake skill to reflect the new discovery behavior, phase order (automation before editing), and orchestrator-managed repo setup. Renamed `dashboard-deployment.md` → `portal-deployment.md` and updated mkdocs nav.
- **Design decision:** Project repo naming is the user's choice. The project ID is defined during intake. Showroom and automation repos use the project ID for consistent naming (`<project-id>-showroom`, `<project-id>-automation`).
- **Lesson learned:** The skills-plugin submodule pushes to the remote, but the local clone at `~/devel/publishing-house/rhdp-publishing-house-skills` is separate. Always pull the local clone after pushing submodule changes.

### Additional Changes (late session)

- **Empty projects in discovery:** Discovery now lists all projects with a manifest, including fresh ones that haven't started intake. Shows "(new project — needs intake)" for empty manifests.
- **`current_phase` not deprecated:** Removed the deprecated comment from the template manifest. Field is actively used by the orchestrator; portal can derive state independently if it wants.
- **RCARS vetting for all modes:** Fixed incorrect restriction that said vetting was unavailable for `self_published`. RCARS vetting is available for both deployment modes.
- **Intake simplification (design only):** Agreed to simplify intake from 3 entry paths to 2: "I have a spec" and "I have an idea." Opening question should be conversational ("tell me about your idea") not structured. Not yet implemented.
- **Backlog from Sha meeting:** Captured four long-term items — prototype deployment mode, RCARS-driven prototyping, customizable skills with include mechanism, end-to-end build+deploy vision.

### Open Items for Next Session

**1. Intake simplification** (priority)

Simplify intake entry paths from 3 to 2. Redesign the opening question flow to be
conversational rather than structured. This is the first impression of the system.

**2. Test phase-gate repo creation**

Showroom repo gate (before writer) and automation repo gate (before 7c) are implemented
but untested. Test with ex-ph-sample or by nulling `integrations.showroom_repo` on an
existing project.

**3. DISCUSS: PH development team design**

Still open from 2026-04-21. Need a contributor spec that defines skill contracts,
state management boundaries, blocker surfacing, and isolated testing.

**4. LONGTERM: PH chatbot UI**

Unchanged from 2026-04-21. Future design effort.

**5. AgnosticD: Split ocp4_workload_field_content**

Unchanged from 2026-04-21. Separate workstream.

**6. Subagent-per-module writing**

Unchanged from 2026-04-21. Parked.

---

## 2026-04-21

### Session Summary

Full skills redesign implemented and tested end-to-end with the RHBK OIDC lab
(`ex-instruction-test`). Reviewed all phases: intake, writing, automation. Documented
12 issues, resolved them all in one implementation pass. All changes committed and pushed.

### What Was Done

- Skills redesign (deployment modes, worklog, smart intake, git sync) — complete
- Intake: Environment section replaces Infrastructure+Automation, simplified repo setup, Showroom required by default
- Orchestrator: strict phase order (writing before automation), worklog routing, project discovery from any directory
- Automation: AsciiDoc-first 7a, per-user-cluster vs shared-cluster topology question, 7c writes worklog entries for blockers, Showroom in provision_data
- Automation manifest format: self_published infrastructure taxonomy (field-per-user-cluster, field-shared-cluster)
- GitOps guide: rewritten around ci-template-gitops patterns, two-role model (field_content_cluster + field_content_tenant), eventual consistency
- Template: removed journal.md (superseded by worklog.yaml), content/ and automation/ now submodules
- Docs: refreshed getting-started, how-it-works, portal.md (was dashboard.md), README, skills README

### Open Items for Next Session

**1. DISCUSS: PH development team design**

Nate owns the orchestrator, overall design, and the contributor standards. Individual
skills (writer, automation, editor) should be ownable by other contributors without
needing to understand the whole system.

Need to write a **contributor spec** that defines:
- What a skill MUST read from the manifest/spec before starting
- What state a skill MUST update when it completes
- What a skill MUST NOT touch (phase-level transitions belong to the orchestrator)
- How a skill surfaces blockers (worklog entries, not improvised fields)
- How to test a skill in isolation

This is the prerequisite for delegating skill ownership to other team members.

**2. LONGTERM: PH chatbot UI**

Instead of running Claude Code or Cursor locally, a hosted chatbot runs the skills on
the user's behalf. Users interact via browser — no local tooling required. Would tie
RCARS, Publishing House, and the portal together into a single entry point.

This is a future design effort, not near-term implementation.

**3. AgnosticD: Split ocp4_workload_field_content**

Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD
apps and return immediately (no health waiting). ArgoCD eventual consistency handles
operator → CR ordering. Field Source CI runs both in sequence without waiting between.
This is a separate workstream in the AgnosticD repo.

**4. Subagent-per-module writing**

For large labs (2+ hours, 6+ modules), writing could use isolated subagents per module
to avoid context accumulation. Parked — revisit when scale becomes a real problem.
