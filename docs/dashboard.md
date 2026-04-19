# Portal

The RHDP Publishing House Portal provides cross-project visibility into the content lifecycle. While individual authors interact with the CLI skills, the portal gives managers and PMs a single view across all active projects.

## Registering a Project

Navigate to the **Register** page and provide:

- **Project Name** — a display name for the dashboard
- **GitHub Repository URL** — SSH or HTTPS. The repo must contain `publishing-house/manifest.yaml`.

On submit, the dashboard fetches the manifest, parses lifecycle phases, and adds the project to the database. You'll be redirected to the project detail page.

## Pipeline View

The **Pipeline** page shows a kanban board with 8 columns mapping to lifecycle phases:

| Column | Manifest Phases |
|--------|----------------|
| Intake | intake, vetting, spec_refinement |
| Approval | approval |
| Writing | writing |
| Automation | automation |
| Editing | editing |
| Code & Security | code_security_review |
| Final Review | final_review |
| Ready | ready_for_publishing |

Each project appears as a card in the column of its furthest-along active phase. Cards show the project name, module count, and assignees.

The recommended flow is writing → automation → editing. Automation often requires content changes (paths, environment variables, hostnames), so editing runs last to avoid editing twice.

## Projects Table

The **Projects** page shows a searchable table of all registered projects with:

- **Project name** — clickable link to the detail page
- **Module count** — number of writing modules
- **Assignees** — everyone assigned across all phases
- **Phase progress bar** — 8 colored segments showing which phases are complete, active, or pending
- **Actions** — refresh (re-fetch manifest from GitHub), edit (change name/repo URL), delete (remove from dashboard)

## Project Detail

Click a project name to see the full detail view:

### Phase Progress Bar

A labeled bar across the top showing all 8 phase groups with completion/active status.

### Phase Accordions

Each lifecycle phase is an expandable section. Click to expand and see:

- **Completion date** — when the phase was finished (shown in the header)
- **Assignees** — who worked on this phase
- **Artifacts** — file paths linked directly to the file in the GitHub repo
- **Phase-specific content:**
    - **Writing** — module list with individual status (pending, in progress, drafted, approved) and links to content files and review files
    - **Automation** — substep status (catalog item, requirements, automation code, testing, e2e checks), catalog path, AgnosticV repo/branch, and automation file list
    - **Approval** — who approved it
    - **Spec Refinement** — list of changes made
    - **Vetting** — RCARS result (approved, revise, rejected)

Pending phases show a dependency hint explaining what must complete first.

### Sidebar

- **Project Info** — type, owner, autonomy level, created date, registered date
- **Links** — GitHub repo, Showroom repo, automation repo (when set in the manifest)
- **Assignees** — listed with their phase assignment

## Refreshing Data

The dashboard caches manifest data in PostgreSQL. Data is refreshed in two ways:

- **Nightly** — a scheduled job re-fetches all manifests from GitHub at 2 AM
- **Manual** — click the refresh button (⟳) on any project in the table or detail view

After refreshing, phase status, dates, assignees, and artifacts update to match the latest manifest in the repo.

## Editing a Project

Click the pencil icon in the projects table to update a project's name or GitHub repo URL. Changing the URL triggers an automatic manifest refresh from the new location.

## Manifest Requirements

For a project to display correctly, its `publishing-house/manifest.yaml` must include:

```yaml
project:
  name: "Project Title"
  owner: "github-username"     # Shown in project detail sidebar
  type: "workshop"             # workshop or demo
  autonomy: "supervised"
  created: "2026-04-01"

lifecycle:
  phases:
    <phase_name>:
      status: "pending"        # pending | in_progress | completed | skipped
      completed_at: null       # ISO datetime when completed (YYYY-MM-DD HH:mm)
      assignees: []            # GitHub usernames working on this phase
      artifacts: []            # File paths (linked to GitHub in the dashboard)
```

The `completed_at`, `assignees`, and `artifacts` fields drive what appears in the phase accordions. If they're missing, the accordion shows "None" for artifacts and no date.

The dashboard also tries `manifest.yaml` at the repo root as a fallback if the standard path isn't found.
