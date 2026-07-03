# Spec & Gate Validation Hardening — Intake Through Writing

**Jira:** RHDPCD-170
**Date:** 2026-07-03
**Author:** Nate Stephany
**Status:** Design

---

## Overview

Harden the deterministic (Python, no LLM) validation checks across the full intake-to-review pipeline. Ensure the approved spec is structurally correct, locked at approval, and enforced at every downstream gate.

The work splits into two parts: Part 1 hardens the intake and approval gate with structural checks and controlled vocabulary. Part 2 adds a spec contract snapshot at approval and enforces it at every downstream gate.

### Architecture: Approach B — New SpecContractService

Extend existing services where the work naturally fits (PhaseEngine for phase validation, SpecValidator for structural checks). Create one new service — `SpecContractService` — that owns the full spec contract lifecycle: snapshot creation, drift detection, and content compliance comparison. GateService orchestrates by calling the right services at each gate.

### Design Principles

- Deterministic Python checks are the default. LLM evaluation is advisory, never a gate blocker on its own.
- The approval gate creates a locked contract. Downstream gates enforce it at every checkpoint.
- How content gets written is the author's choice. What gets validated is identical regardless.
- Error messages are specific and actionable: file name, expected heading, what was found instead, line number.
- Fresh read from git (via GitHub API) at every gate request. Cached data is for status display and early warnings only.

---

## Part 1: Intake & Approval Gate

### 1. Phase Integrity Check

**Where:** `PhaseEngine` — new method `validate_phase_profile(manifest, deployment_mode)`

Compares phases in `manifest.lifecycle.phases` against the expected phase profile for the deployment mode. Returns extra phases (in manifest but not in profile) and missing phases (in profile but not in manifest).

**Runs at:**
- Every gate request in GateService, before any other checks
- Every manifest sync in RefreshService

**Behavior:** Gate rejects with a specific message if phases don't match:

> "Manifest lifecycle does not match the 'rhdp_published' profile: unexpected phase 'custom_review', missing phase 'security_review'."

**Edge case:** Phases with `status: skipped` must still be present in the manifest. Skipping is a valid state; removing the phase entirely is not. The profile defines the shape; status defines progress.

### 2. Controlled Vocabulary

**Where:** `SpecValidator` — vocabulary validation methods. Database-backed lists managed via Central API and dashboard.

**Three vocabulary lists:**

| List | Initial Values | Matching |
|------|---------------|----------|
| **Content type** | `lab`, `demo` | Exact, case-insensitive |
| **Difficulty level** | `beginner`, `intermediate`, `advanced` | Exact, case-insensitive |
| **Product names** | ~30 official Red Hat products | Normalization + abbreviation map |

All three are expandable lists stored in the database, seeded from a starter set on first deployment, and managed via the Central dashboard after that.

#### Product name matching — two-layer normalization

Product names use a two-layer matching approach to accept common shorthand without maintaining exhaustive alias lists:

**Layer 1 — Normalization:** Strip "Red Hat" prefix, lowercase, collapse whitespace, strip trailing version numbers. This handles the majority of naming variations automatically:
- "Red Hat OpenShift Virtualization" → `openshift virtualization`
- "OpenShift Virtualization" → `openshift virtualization`
- Both match. No aliases needed.

**Layer 2 — Abbreviation map:** Small, stable set of well-known acronyms (~15-20 entries):
- `OCP` → OpenShift
- `AAP` → Ansible Automation Platform
- `RHEL` → Enterprise Linux
- `RHOAI` → OpenShift AI
- `CNV` → OpenShift Virtualization
- `RHDH` → Developer Hub

Adding a new product is one line in the canonical list. Adding a new acronym is one line in the abbreviation map. Minimal ongoing maintenance.

**Validation behavior:** Accept anything that normalizes to a known product. Reject completely unrecognized products. No suggestions, no corrections — if we recognize it, it passes.

**Error message:**

> "Product 'Cloud Nexus Platform' is not recognized. If this is a valid Red Hat product, add it via the Publishing House dashboard."

#### Dashboard management

Central exposes API endpoints for CRUD operations on all three vocabulary lists. The dashboard provides a simple admin page for adding, removing, and editing entries. This avoids requiring Python file edits to manage vocabulary.

#### Future expansion

The hardcoded starter list is validated against RCARS catalog data during initial coding. Over time, as RCARS data quality improves, the product list can be expanded from RCARS data. But RCARS is not the authority — the curated list is.

### 3. Module Spec Validation

**Where:** `SpecValidator` — new method `validate_module_specs(spec_dir)`

Iterates over `spec/modules/module-*.md` files and checks each against required sections from the module outline template:

- Brief Overview
- Audience and Time
- What You Will See, Learn, and Do (or "See/Learn/Do")
- Lab Structure (with at least one table row)
- Key Takeaways

Same heading-based structural check used for design.md — case-insensitive substring matching. No content quality judgment, just "is the section there and non-empty."

**Additional checks per module:**
- Lab Structure has at least one row in the table
- Duration is specified in Audience and Time
- No template placeholders (reuses existing placeholder regex)

**Does NOT check:**
- Detailed Steps (optional, varies by module complexity)
- Infrastructure Notes (explicitly optional per template)
- Content quality or step accuracy (that's the human approver's job)

**Runs at:** Approval gate — incomplete module specs block approval. Also runs as part of spec drift detection on every sync.

**Error messages are per-file and per-section:**

> "module-02-deploying-vms.md: Missing required section 'Key Takeaways'. Found sections: Brief Overview, Audience and Time, See/Learn/Do, Lab Structure."

### 4. Template Rename

**Where:** `rhdp-publishing-house-template` repo

Rename `publishing-house/spec/SPEC-TEMPLATE.md` to `publishing-house/spec/module-outline-template.md`.

Current name is ambiguous — it's unclear whether it's a template for design.md or for module outlines. Since Central's SpecValidator parses module specs against this template's sections, the name must be unambiguous.

**No backwards compatibility.** The old name is not supported. Any code referencing `SPEC-TEMPLATE.md` is updated to the new name. Existing project repos still have the old file — that's fine, it's a read-only reference document, not something Central parses from project repos.

---

## Part 2: Post-Approval Gate Enforcement

### 5. Spec Contract Snapshot

**Where:** New `SpecContractService` + new `SpecSnapshot` DB model

#### SpecSnapshot model

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID, PK | |
| `project_id` | UUID, FK, indexed | |
| `snapshot_data` | JSONB | Extracted contract fields |
| `source_commit` | str(40) | Git commit SHA when snapshot was taken |
| `is_current` | bool | Only one active snapshot per project |
| `superseded_by` | UUID, FK to self, nullable | Links to replacement if re-approved |
| `created_at` | datetime | |

#### Snapshot data structure

Pure Python extraction from design.md + module specs. No LLM in the extraction chain.

```json
{
  "content_type": "lab",
  "difficulty": "intermediate",
  "products": ["OpenShift", "OpenShift Virtualization"],
  "learning_objectives": ["Deploy a VM on OpenShift...", "Configure live migration..."],
  "module_count": 4,
  "modules": [
    {"title": "Introduction to OCP Virt", "duration": "20 min"},
    {"title": "Deploying VMs", "duration": "25 min"},
    {"title": "Live Migration", "duration": "20 min"},
    {"title": "Troubleshooting VMs", "duration": "25 min"}
  ],
  "total_duration": "2 hours",
  "section_counts": {
    "design_md": 9,
    "module_specs": 4
  }
}
```

Extraction uses Python markdown parsing — heading extraction, table parsing, bullet list parsing. Same techniques SpecValidator already uses. If the parser can't extract a field, that's a validation error — the markdown isn't following the template.

**Error messages must be specific about extraction failures:**

> "design.md: Could not extract learning objectives. Expected a bulleted list under '## Learning Objectives' (line 18), but found a paragraph. Use '- ' bullet syntax."

#### When snapshots are created

- **Approval gate passes** → SpecContractService creates the initial snapshot, marks `is_current = True`
- **Spec re-approved after modification** → New snapshot created, old snapshot gets `is_current = False` with `superseded_by` pointing to the new one

Snapshot history is preserved — trace back through `superseded_by` to see contract evolution. Only the current snapshot is used for downstream gate comparisons.

### 6. Spec Compliance Checks at Downstream Gates

**Where:** `SpecContractService` — methods `check_spec_drift()` and `check_content_compliance()`

Two checks run at the **writing→editing** and **editing→code_review** gates:

#### Check 1 — Spec drift detection

Re-extract contract fields from current design.md + module specs and compare against the current snapshot.

- **All fields match** → Spec is still approved, proceed
- **Contract fields changed** → Flag as modified, gate blocks:

> "Spec has been modified since approval. Changed fields:
> - Module count: 4 → 5 (added: 'Troubleshooting VMs')
> - Learning objective added: 'Diagnose VM boot failures'
> Re-approval required before proceeding."

#### Check 2 — Content compliance (deterministic)

Parse AsciiDoc content and compare structural metadata against the snapshot:

- Module count — count of module page files
- Module titles — from nav.adoc entries or page titles
- Presence of content for each module (non-empty files)

> "Content does not match the approved spec. Expected 4 modules, found 3. Missing: 'Troubleshooting VMs'."

This is the deterministic structural check. Whether the content *quality* matches what the spec promises is handled by the advisory LLM check and ultimately by human reviewers.

#### Two-tier drift model

| Tier | What changes | Detection | Action |
|------|-------------|-----------|--------|
| **Structural integrity** | Sections present, no placeholders, structure valid | Automated on every sync | Auto-pass, spec health stays green, snapshot unchanged |
| **Contract field drift** | Module count/titles, products, learning objectives, difficulty, durations, content type | Automated on every sync + gate | Blocks downstream gates, requires human re-approval via approval gate |

#### Advisory content alignment check (non-deterministic)

At the **writing→editing gate** and **on-demand via MCP**, Central runs a lightweight LLM check comparing AsciiDoc content against the approved spec snapshot.

**Model tier:** Lightweight / open-source preferred (e.g., model running on LightMaaS). Not a frontier model — this is a basic alignment check, not a deep review. Good visibility for showing PH uses appropriate model tiers and doesn't rely on frontier models for everything.

**Prompt pattern:** "Here's what the spec says each module should cover. Here's the AsciiDoc content. For each module, does the content appear to address the spec? One sentence per module."

**Result:** Advisory only, never blocks the gate. Caution flags included in the gate response:

> "Advisory alignment check:
> - Module 1 (Introduction): Aligned
> - Module 2 (Deploying VMs): Aligned
> - Module 3 (Live Migration): ⚠ Spec mentions live migration between nodes, content only covers cold migration
> - Module 4 (Troubleshooting): Not yet written"

**Two trigger points:**
1. **Automatic at writing→editing gate** — runs after deterministic checks pass, results included in gate response
2. **On-demand via MCP call** — anyone can ask Central "check my work" at any point, even mid-writing with incomplete modules. Same check, same report.

### 7. Spec Lock Model — Summary

The approved snapshot is the locked contract. The lock works as follows:

1. **Approval gate passes** → Snapshot created. This is the contract.
2. **Author writes content** → Deterministic checks run on every sync (cheap Python). If spec structure is intact and no contract field values changed, everything is green.
3. **Author modifies the spec** → Drift detection catches it. Contract fields changed → spec flagged as "modified since approval." Downstream gates block until re-approved.
4. **Re-approval needed** → Author goes back through the approval gate. Full flow: Python structural checks → LLM quality review → human approver. New snapshot replaces old.
5. **Downstream gates** → Always compare against the latest approved snapshot. Always verify the spec is in "approved" state. Both must pass.

**Why the lock matters:** Without it, anyone could rewrite the spec to match whatever they delivered, making the approval gate meaningless. The spec is a contract between the author and the reviewers who approved it.

### 8. Writing Mode Choice

**Where:** Manifest field + orchestrator behavior + Central awareness

After the approval gate passes, the orchestrator asks:

> "Will you be providing the content yourself, or would you like Publishing House skills to help write it?"

Recorded in the manifest:

```yaml
lifecycle:
  phases:
    writing:
      writing_mode: self_provided | assisted
```

**Behavior difference:**
- `assisted` — Orchestrator invokes writer skill for each module
- `self_provided` — Orchestrator skips writer skill, author places content in the repo manually

**Same validation either way.** The writing→editing gate runs identical checks regardless of writing mode. Central knows about the writing mode for reporting and status display, but it doesn't change what gates validate.

This pattern extends to other phases (automation could also be self_provided vs assisted), but this ticket focuses on writing mode only.

---

## Approval Gate Flow — Complete Picture

The approval gate is the most complex gate, with three layers:

1. **Python structural checks (automated, hard gate)**
   - Phase integrity (item 1)
   - Vocabulary validation — content type, difficulty, products (item 2)
   - Design.md section validation (existing SpecValidator)
   - Module spec validation (item 3)
   - No self-approval (existing check)
   - Spec commit unchanged since vetting (existing check)
   - If ANY fail → gate rejects immediately. No LLM review, no human review.

2. **LLM quality review (automated, advisory)**
   - Spec reviewer scores across dimensions (scope, structure, clarity, depth)
   - Produces a report with specific findings
   - Not a gate blocker on its own — feeds into human decision

3. **Human approver (authority)**
   - Receives both: structural check results + LLM quality report
   - Reads the spec (or uses the quality report as a guide)
   - Makes the final approve/reject decision
   - Must be a different person than the author (for rhdp_published)

**After approval:** Snapshot created, writing mode chosen, writing phase begins.

---

## Gate Request Flow — All Gates

Every gate request follows this pattern:

1. **Fresh read from git** of the repo at the requested branch
2. **Parse** manifest, design.md, module specs from git content
3. **Phase integrity check** — manifest phases match deployment mode profile
4. **Structural validation** — appropriate checks for the target gate
5. **Spec drift check** (post-approval gates) — contract fields match snapshot
6. **Content compliance** (post-approval gates) — AsciiDoc matches snapshot
7. **Advisory LLM check** (writing→editing gate) — lightweight content alignment
8. **Gate decision** — approve, reject, or present to human approver
9. **Record GateRecord** — immutable audit trail

Routine manifest syncs run steps 3-5 as a health check (cheap Python). Gate requests always clone fresh and run the full sequence.

---

## Components Changed

| Component | Changes | Repo |
|-----------|---------|------|
| `PhaseEngine` | Add `validate_phase_profile()` | Central |
| `SpecValidator` | Add vocabulary validation, module spec validation | Central |
| `SpecContractService` | **New.** Snapshot creation, drift detection, content compliance | Central |
| `SpecSnapshot` model | **New.** DB model for contract snapshots | Central |
| `VocabularyList` model | **New.** DB model for managed vocabulary lists | Central |
| `GateService` | Call new validators at appropriate gates | Central |
| `RefreshService` | Call drift detection on every sync | Central |
| `MCP gate tools` | Add on-demand content alignment check endpoint | Central |
| `Dashboard` | Add vocabulary management admin page | Central |
| `SPEC-TEMPLATE.md` | Rename to `module-outline-template.md` | Template repo |
| `Alembic migration` | Add SpecSnapshot + VocabularyList tables | Central |

---

## Out of Scope

- LLM-based quality validation improvements (spec reviewer already exists)
- Automation phase self_provided/assisted mode (future, same pattern as writing)
- RCARS-driven automatic product list expansion (future, depends on RCARS data quality)
- Full editorial review automation (editor skill handles this separately)
- Showroom AsciiDoc content quality checks beyond structural metadata
