# PH Skills Consolidation — Architecture Spec

**Date:** 2026-06-29  
**Status:** Draft  
**Author:** Prakhar Srivastava  
**Scope:** Consolidate showroom, agnosticv, and ftl plugins from rhdp-skills-marketplace into rhdp-publishing-house-skills as a multi-plugin package. Remove marketplace dependency for PH users.

---

## Problem

Today PH users need two separate plugin installs:
1. `rhdp-publishing-house-skills` — PH orchestration skills
2. `rhdp-skills-marketplace` — showroom, agnosticv, ftl, health, sandbox-cli

PH skills hard-depend on marketplace skills by name (`showroom:create-lab`, `agnosticv:catalog-builder`). If a user installs PH without marketplace, they get silent failures during writer, editor, and automation phases. There is no version contract between the two repos — they can silently drift.

## Solution

Transform `rhdp-publishing-house-skills` into a **multi-plugin package** — a single git repo that hosts 4 independent Claude Code plugins. One `--plugin-dir` install gives users everything PH needs.

## Critical Constraint: Plugin Names Cannot Change

Claude Code resolves skill calls as `<plugin-name>:<skill-name>`. The plugin name comes from `.claude-plugin/plugin.json` → `"name"` field.

```
showroom plugin (name: "showroom")  →  showroom:create-lab  ✓
agnosticv plugin (name: "agnosticv") →  agnosticv:catalog-builder  ✓
```

If skills moved into the `rhdp-publishing-house` plugin namespace, ALL call sites in PH SKILL.md files would break. Therefore: **each plugin MUST retain its original name in its own plugin.json**.

## Target Structure

```
rhdp-publishing-house-skills/           ← ONE repo, users clone once
├── .claude-plugin/
│   └── plugin.json                     ← name: "rhdp-publishing-house"
├── skills/                             ← PH orchestration skills (unchanged)
│   ├── orchestrator/SKILL.md
│   ├── intake/SKILL.md
│   ├── writer/SKILL.md                 ← still calls showroom:create-lab
│   ├── editor/SKILL.md                 ← still calls showroom:verify-content
│   ├── automation/SKILL.md             ← still calls agnosticv:catalog-builder
│   └── worklog/SKILL.md
│
├── showroom/                           ← NEW — copied from marketplace
│   ├── .claude-plugin/
│   │   └── plugin.json                 ← name: "showroom" (MUST keep this name)
│   ├── skills/
│   │   ├── create-lab/SKILL.md
│   │   ├── create-demo/SKILL.md
│   │   ├── verify-content/SKILL.md
│   │   └── blog-generate/SKILL.md
│   ├── agents/
│   │   ├── scaffold-checker.md
│   │   ├── module-reviewer.md
│   │   ├── file-generator.md
│   │   ├── score-aggregator.md
│   │   └── doc-writer.md
│   └── docs/                           ← reference files (writing guides, etc.)
│
├── agnosticv/                          ← NEW — copied from marketplace
│   ├── .claude-plugin/
│   │   └── plugin.json                 ← name: "agnosticv" (MUST keep this name)
│   ├── skills/
│   │   ├── catalog-builder/SKILL.md
│   │   └── validator/SKILL.md
│   ├── agents/                         ← 9 specialist agents (v2.15.0)
│   │   ├── schema-checker.md
│   │   ├── workload-checker.md
│   │   ├── ocp-infra-checker.md
│   │   ├── sandbox-checker.md
│   │   ├── metadata-checker.md
│   │   ├── config-writer.md
│   │   ├── description-writer.md
│   │   ├── workflow-reviewer.md
│   │   └── README.md
│   └── docs/                           ← reference files (validator checks, shared context schema, etc.)
│
└── ftl/                                ← NEW — copied from marketplace
    ├── .claude-plugin/
    │   └── plugin.json                 ← name: "ftl" (MUST keep this name)
    ├── skills/
    │   ├── content-reader/SKILL.md
    │   ├── solve-writer/SKILL.md
    │   ├── validate-writer/SKILL.md
    ├── agents/
    │   └── rhdp-lab-validator/         ← ftl:rhdp-lab-validator
    └── docs/
```

## What Stays in Marketplace

`rhdp-skills-marketplace` is NOT deleted. It retains:
- `health/` plugin — deployment validation (not PH-dependent)
- `sandbox-cli/` plugin — sandbox management (not PH-dependent)
- Root `README.md`, `CHANGELOG.md`, `install.sh`

The marketplace becomes a **supplementary toolset**, not a PH dependency.

## Plugin Version Tracking

Each subdir plugin maintains its own version in its `plugin.json`. The PH orchestrator skill checks these at session start:

```yaml
# In orchestrator SKILL.md — version gate check
Minimum required versions:
  rhdp-publishing-house: 0.2.0
  showroom: 2.14.0
  agnosticv: 2.15.0    ← requires ph_payload headless mode
  ftl: (TBD)
```

If a plugin is below minimum version → orchestrator surfaces a warning and points to the update command.

## Source of Truth

Each plugin within the combined repo tracks its own version in `plugin.json`. The **version in the combined repo IS the canonical version** — there is no separate source repo that "owns" the skills.

When showroom or agnosticv skills need an update, the PR goes against `rhdp-publishing-house-skills`, not `rhdp-skills-marketplace`.

This is a **one-way migration** — after cut-over, marketplace copies of showroom/agnosticv/ftl are frozen and users are pointed to PH.

## What Changes for Users

| Before | After |
|--------|-------|
| Install `rhdp-publishing-house-skills` + `rhdp-skills-marketplace` | Install only `rhdp-publishing-house-skills` |
| Two separate git repos to pull | One `git pull` updates everything |
| Silent failure if marketplace not installed | All dependencies in one package |
| Version drift between repos | Single repo, co-versioned |

## Non-Goals

- Do NOT rename `showroom`, `agnosticv`, or `ftl` plugin names unless doing Option B below (full atomic rename)
- Do NOT merge all skills into one flat `skills/` dir — loses plugin namespace isolation
- Do NOT archive `rhdp-skills-marketplace` immediately — health and sandbox-cli users still depend on it

---

## Option B: Rename Plugins During Consolidation

**Status:** Under discussion. Current plugin names may be renamed during consolidation.

The consolidation PR is the **only moment** where renaming is low-cost. After consolidation, a rename requires a second round of user migration.

### Proposed Names (TBD — decision pending)

| Current name | Proposed new name | Skill call example |
|---|---|---|
| `showroom` | `rhdp:showroom` or `content` or `lab-authoring` | `lab-authoring:create-lab` |
| `agnosticv` | `rhdp:catalog` or `catalog` or `agv` | `catalog:catalog-builder` |
| `ftl` | `rhdp:ftl` or `lab-testing` or `ftl` | `lab-testing:solve-writer` |

### If Renaming: Steps (ATOMIC — must all happen in same PR)

**Rule:** Renaming is all-or-nothing in a single commit. Partial renames cause broken installs for users mid-pull.

#### Step R-1: Decide the new names
Agree on names before touching any files. Names must be:
- Short (users type them as `/skill-name:create-lab`)
- Descriptive without being verbose
- Consistent with the `rhdp-publishing-house` naming pattern

#### Step R-2: Update each `plugin.json`

```json
// showroom/.claude-plugin/plugin.json
{
  "name": "<NEW-NAME>",         // ← change this
  "version": "2.14.0",
  ...
}
```

Same for agnosticv and ftl plugin.json files.

#### Step R-3: Update ALL call sites in PH SKILL.md files

These files call the old names and must ALL be updated:

| File | Current calls | Must change to |
|------|--------------|---------------|
| `skills/writer/SKILL.md` | `showroom:create-lab`, `showroom:create-demo` | `<new-name>:create-lab` |
| `skills/editor/SKILL.md` | `showroom:verify-content` | `<new-name>:verify-content` |
| `skills/automation/SKILL.md` | `agnosticv:catalog-builder`, `agnosticv:validator` | `<new-name>:catalog-builder` |
| `skills/orchestrator/SKILL.md` | `agnosticv:catalog-builder`, `agnosticv:validator` | `<new-name>:catalog-builder` |
| `skills/writer/references/writing-standards.md` | `showroom:create-lab`, `showroom:create-demo` | update |
| `skills/editor/references/editing-checklist.md` | `showroom:verify-content` | update |
| `skills/automation/references/automation-patterns.md` | `agnosticv:catalog-builder`, `agnosticv:validator` | update |

#### Step R-4: Update CHANGELOG

```markdown
## [v0.2.0] - YYYY-MM-DD

### BREAKING: Plugin names changed

Old → New:
- `showroom` → `<new-name>`
- `agnosticv` → `<new-name>`
- `ftl` → `<new-name>`

Any scripts or settings referencing old skill names must be updated.
```

#### Step R-5: Update migration guide

The migration plan spec (`ph-skills-migration-plan.md`) must be updated to tell users:
- Old marketplace skill names no longer work
- New names to use
- How to update any personal scripts or notes that reference old names

#### Step R-6: Search for any other references

```bash
# Find all remaining old-name references across the repo
grep -r "showroom:" . --include="*.md" | grep -v ".git"
grep -r "agnosticv:" . --include="*.md" | grep -v ".git"
grep -r "ftl:" . --include="*.md" | grep -v ".git"
```

All hits must be updated before the PR is opened.

### Cost vs. Benefit of Renaming

| Factor | Rename during consolidation | Rename later |
|--------|---------------------------|-------------|
| Number of PRs | 1 (same consolidation PR) | 2 (consolidation + rename) |
| User disruption | 1 migration event | 2 migration events |
| Call site updates | ~7 files | ~7 files |
| Reviewer complexity | Higher (bigger PR) | Separate, smaller PR |
| Risk | Must be atomic — no partial | Same risk, second round |

**Recommendation:** If plugins will be renamed, do it during the consolidation PR. Waiting costs nothing architecturally but adds a second user migration event later.
