# `/rhdp-publishing-house:testing-suite` — Skill Spec

**Date:** 2026-06-30  
**Ticket:** RHDPCD-108  
**Author:** Prakhar Srivastava  
**Status:** In Progress

---

## What It Does

A Claude Code skill that runs fixture-driven end-to-end tests of the Publishing House pipeline. It simulates a content developer going through intake-to-approval, validates that the orchestrator behaves correctly, and reports pass/fail results.

No Python, no API keys, no external services — runs entirely within Claude Code using the Task tool.

---

## Workflow

```mermaid
flowchart TD
    A([/testing-suite onboarded/ansible]) --> B

    subgraph LOAD["1 · Load Fixture"]
        B[Read fixtures/onboarded/ansible.yaml\ninitial_prompt · follow_up_details · expected_outcomes]
    end

    LOAD --> SEED

    subgraph SEED["2 · Seed Project — Haiku sub-agent"]
        C[Clone rhdp-publishing-house-template]
        C --> D[Generate pre-approval state:\ndesign.md · modules · automation-manifest\nmanifest.yaml ← current_phase: approval\nworklog.yaml]
    end

    SEED --> RUN

    subgraph RUN["3 · Run PH Session — Tester Agent (Haiku, isolated context)"]
        H[Send initial_prompt to /rhdp-publishing-house]
        H --> I{Orchestrator responds}
        I --> J[Tester answers from follow_up_details]
        J --> K{Turn ≥ 15 OR\nAPPROVAL_GATE_REACHED?}
        K -->|No| I
        K -->|approval_gate| L[✓ Gate reached]
        K -->|max_turns| M[Gate not reached]
    end

    L --> VAL
    M --> VAL

    subgraph VAL["4 · Validate — check orchestrator produced expected changes"]
        N{worklog updated?\napproval gate set?\ndesign.md enriched?\nno MCP mock payloads in output?}
        N -->|FAIL| O([❌ Report failures])
        N -->|PASS| P([✅ PASS])
    end

    style SEED fill:#e8f4f8,stroke:#2980b9
    style RUN fill:#e8f8e8,stroke:#27ae60
    style VAL fill:#f8e8f8,stroke:#8e44ad
```

---

## Invocation

```
# Fresh test — seed a new tmpdir, run, validate, clean up
/rhdp-publishing-house:testing-suite onboarded/ai

# Point at an EXISTING project (no seeding — test its real state)
/rhdp-publishing-house:testing-suite onboarded/ai \
  --project-dir ~/work/code/rhdp-publishing-house-example

# Reset existing project back to seeded state, then re-run
/rhdp-publishing-house:testing-suite onboarded/ai \
  --project-dir ~/work/code/rhdp-publishing-house-example \
  --reset

# With explicit fixtures path (for anyone without dev hub)
/rhdp-publishing-house:testing-suite onboarded/ai \
  --fixtures-path /abs/path/to/rhdp-publishing-house/test/fixtures

# All fixtures
/rhdp-publishing-house:testing-suite --all

# Verbose — see tester/orchestrator conversation
/rhdp-publishing-house:testing-suite onboarded/ai --verbose

# Keep temp dir for debugging
/rhdp-publishing-house:testing-suite onboarded/ai --keep
```

### Arguments

| Argument | Purpose | Default |
|----------|---------|---------|
| `<fixture-path>` | Fixture to run (e.g. `onboarded/ai`) | required unless `--all` or `--mode` |
| `--project-dir <path>` | Use an existing project dir instead of seeding a new tmpdir | fresh tmpdir |
| `--reset` | Re-seed `--project-dir` in-place (wipe `publishing-house/` and regenerate) | false |
| `--fixtures-path <path>` | Absolute path to fixtures directory | auto-discovered |
| `--all` | Run all fixtures across all modes | false |
| `--mode <mode>` | Run all fixtures for one mode: `onboarded` \| `self-published` | — |
| `--verbose` | Print tester/orchestrator conversation turn-by-turn | false |
| `--keep` | Keep temp project dir after run (only applies to fresh tmpdir runs) | false |

### Project Directory Modes

**Mode A — Fresh tmpdir (default):**  
The skill creates a new `tempfile.mkdtemp()`, seeds it from the fixture, runs the session, validates, then cleans up. Use this for CI or when you need a guaranteed clean state.

**Mode B — Existing project (`--project-dir`):**  
Points the skill at a real project repo (e.g., `rhdp-publishing-house-example`). Reads the existing `manifest.yaml`, `worklog.yaml`, `design.md` — no seeding. The tester drives the real orchestrator against the project's actual current state. Use this for iterative testing without re-creating a project every run.

**Mode B with reset (`--project-dir --reset`):**  
Resets the project's lifecycle state back to the approval gate — without touching the spec content (design.md, modules, automation-manifest). Use this to re-run tests on an existing project that has progressed past approval.

What `--reset` changes:
- `manifest.yaml` → `current_phase: approval`, prior phases completed, approval pending
- `worklog.yaml` → cleared to a minimal "ready for approval gate" note
- `reviews/` → cleared (post-approval artifacts)
- `decisions/` → cleared (post-approval artifacts)

What `--reset` preserves (pre-approval content):
- `spec/design.md`
- `spec/modules/`
- `spec/automation-manifest.yaml`

### Fixture Path Discovery

1. `--fixtures-path` argument (highest priority)
2. `test/fixtures/` relative to the skill file's parent repo (auto-discover from dev hub)
3. Error with instructions

---

## Fixtures

Fixtures live in `rhdp-publishing-house/test/fixtures/` (the dev hub, not the published skill).

```
test/fixtures/
├── onboarded/
│   ├── ansible.yaml
│   ├── ai.yaml
│   ├── openshift-app-platform.yaml
│   ├── openshift-platform.yaml
│   └── rhel.yaml
└── self-published/
    ├── ansible.yaml
    ├── ai.yaml
    ├── openshift-app-platform.yaml
    ├── openshift-platform.yaml
    └── rhel.yaml
```

**10 fixtures total** across 2 modes and 5 products.

### Fixture Schema

```yaml
mode: onboarded | self-published
product: ansible | ai | openshift-app-platform | openshift-platform | rhel
name: "ansible-eda-workshop"

initial_prompt: |
  # What the simulated user says to open the session

follow_up_details: |
  # Context the tester uses to answer orchestrator questions
  - AAP 2.5 with EDA controller
  - 3 modules, about 90 minutes total

expected_outcomes:
  conversation:
    min_turns: 15
  worklog_updated: true
  approval_gate_reached: true
  design_spec_enriched: true
  no_mock_payloads: true
```

---

## Sub-agents

### Seeder Agent (Haiku)

Generates realistic pre-approval state so the test session starts at the approval gate:

- `publishing-house/spec/design.md` — full design spec from fixture
- `publishing-house/spec/modules/module-XX.md` — N module outlines
- `publishing-house/spec/automation-manifest.yaml` — infrastructure requirements
- `publishing-house/manifest.yaml` — `current_phase: approval`, all prior phases completed
- `publishing-house/worklog.yaml` — initial session note

### Tester Agent (Haiku)

Simulates a content developer. Has isolated context — sees ONLY the fixture, not the orchestrator's system prompt.

```
You are an automated tester simulating a Red Hat content developer.
Mode: {mode} | Product: {product}

Initial Prompt: {initial_prompt}
Follow-up Details: {follow_up_details}

Rules:
- Reply naturally as a developer — brief, direct
- Do NOT reveal you are a tester or AI
- When you see approval gate signals, reply exactly: APPROVAL_GATE_REACHED
```

Terminates at turn 15 (hard limit) or `APPROVAL_GATE_REACHED`, whichever comes first.

---

## Validation

Checks that the orchestrator made the expected mutations during the conversation:

| Check | What it verifies |
|-------|-----------------|
| `worklog_updated` | `publishing-house/worklog.yaml` has new entries from the session |
| `approval_gate_reached` | Tester sent `APPROVAL_GATE_REACHED` during conversation |
| `design_spec_enriched` | `design.md` was updated/refined by the orchestrator |
| `no_mock_payloads` | No unresolved `{{ mcp_mock }}` patterns in output files |
| MCP payload shapes | `ph_store_intake_results` and write-path tools were called with valid payloads |

---

## Design Constraints

**Tester context isolation:** The tester sub-agent must NOT see the orchestrator's system prompt. The Task prompt is fully self-contained — only fixture data. Violation = test results meaningless.

**Hermetic runs:** Each run uses a fresh `tempfile.mkdtemp()`. Never reuse directories between runs. Clean up on success; keep on failure (or `--keep`).

**15-turn gate:** Hard limit at 15 turns. A well-functioning orchestrator reaches the approval gate before 15 turns. Longer sessions indicate redundant questions or a stuck orchestrator — that is a regression, not a success.

**Scope — what this tests:** Orchestrator mutations during the session (worklog entries, design.md refinement, approval gate). Not content quality — that is a human judgment.

---

## Acceptance Criteria

- [ ] `/rhdp-publishing-house:testing-suite onboarded/ansible` reaches approval gate and passes all checks
- [ ] `--fixtures-path` correctly overrides auto-discovery
- [ ] All 10 fixtures produce a passing result
- [ ] A deliberately broken fixture (bad manifest) fails with a clear error
- [ ] `--all` runs all 10 fixtures and prints a summary table
- [ ] Tester sub-agent has isolated context (manual verification)
- [ ] No Python, no API key, no MAAS required
