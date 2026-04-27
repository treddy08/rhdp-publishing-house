# Publishing House — Backlog

Development backlog for the RHDP Publishing House skill suite. Session notes and completed work live in [WORKLOG.md](WORKLOG.md).

---

## Active / Near-term

### RCARS API integration for vetting
The intake skill references `/recommend` which does not exist in RCARS v2. The real endpoint is `POST /api/v1/advisor/query` (async, returns a job_id) + `GET /api/v1/advisor/query/{job_id}/result` to poll results. Needs:
- Update intake skill to use the real v2 API contract
- Handle async job flow (submit → poll → present results)
- Resolve internal auth: RCARS API has no external route; PH needs to call it cluster-internally. For now, direct service call to `rcars-api.rcars-dev.svc:8080` is simplest. Auth TBD (see access architecture item below).

**Depends on:** RCARS v2 deployed (done as of 2026-04-26). No brainstorm needed — clear implementation task.

---

## Needs Brainstorm

### Prototype deployment mode + RCARS-driven prototyping
A third deployment mode: **prototype**. No GitOps repo, no stored automation. PH uses RCARS to find the closest existing RHDP catalog item to what's being requested, learns how that item is built, orders it via Babylon, and customizes the running environment to match the demo need. Fast, disposable, no publishing overhead.

This merges two originally separate backlog items (prototype mode + RCARS-driven prototyping) because they are the same thing — RCARS is the intelligence layer that makes prototype mode work.

**Why:** Not everything needs to be a published catalog item. A working demo environment for a specific event or meeting should take hours, not weeks.

**Connects to:** End-to-end build+deploy vision (if prototype mode proves the model, full lifecycle is the natural extension).

**Depends on:** RCARS integration working (PH can already call RCARS for vetting; prototype needs RCARS find-closest-match and eventually a Showroom live-read endpoint).

---

### PH access architecture — MCP server + portal chatbot
Two access modes for PH, same experience:

| Mode | Who | How PH runs | How PH talks to RCARS |
|------|-----|-------------|----------------------|
| **Local** | Has Claude Code + Anthropic access | Skills plugin in CC/Cursor | MCP server handles RCARS calls transparently |
| **Hosted** | Everyone else | PH portal chatbot | Portal backend calls RCARS directly (same cluster) |

The MCP server (originally planned as a cheap status query layer) now also owns the RCARS integration and auth bridge for local users. Users should never see a token, API key, or endpoint URL — PH handles it.

The portal chatbot moves from "LONGTERM" to near-term: it's the access path for users who don't have CC or Anthropic model access, not just a convenience UI.

**Brainstorm scope:** MCP server design, what tools it exposes, how local and hosted modes differ at the transport layer (not the skill logic), auth model for RCARS in both contexts, what the chatbot needs from the portal backend.

**Connects to:** RCARS integration, prototype deployment mode, end-to-end build+deploy.

---

### PH test harness skill
A dedicated skill (`rhdp-publishing-house:test`) that validates the PH skill suite before releases. Required before PH becomes the standard for new content — a broken release cannot be discovered through hours of manual testing.

**Design direction:**
- Fixture-based: versioned project directories at known states (pre-intake, post-intake/pre-writing, mid-writing, etc.)
- Scripted inputs per fixture, run via Claude Code CLI in batch mode
- Structural assertions on file system outcomes: file existence, manifest YAML field values, gate blocking behavior
- Does NOT test content quality (LLM non-determinism) — tests gates, routing, and artifact creation
- Runs pre-release, not on every commit

**Brainstorm scope:** Fixture design, input scripting approach, assertion framework, what constitutes "passing", how to version and evolve the test suite as skills change.

---

## Medium Priority

### Customizable skills
Include/hook mechanism at the start of each skill for user overrides — writing style, naming conventions, review criteria. Users tweak behavior independently while still picking up core PH skill updates.

- Additive and optional: skills work without customizations; overrides extend, not replace
- Exception: code review, security review, and content review skills must stay standardized — quality gates are not customizable

### PH development team design / contributor spec
Keep PH modular so skill ownership can be delegated. A contributor spec defines:
- What a skill MUST read from manifest/spec before starting
- What state a skill MUST update when it completes
- What a skill MUST NOT touch (phase-level transitions belong to the orchestrator)
- How a skill surfaces blockers (worklog entries)
- How to test a skill in isolation

Not blocking current work, but should inform design decisions now so we don't paint ourselves into a corner.

### Dashboard kanban — content + automation display
Content and automation run concurrently and iterate together until both are done. The portal kanban needs a way to show this overlap without awkwardly duplicating cards or placing the project in the wrong column. Current approach (furthest-along active column) is functional but not ideal.

---

## Long-term

### End-to-end build + deploy
PH handles the full lifecycle end-to-end — someone comes with a need, PH builds the content, automation, and deploys it for them. No manual steps. Natural follow-on once prototype mode proves the model.

### MCP orchestrator
Move the orchestrator from a skill to a hosted MCP server (FastAPI on OpenShift). Exposes tools like `ph_get_status()`, `ph_advance_phase()`. Cheap structured lookups replace expensive skill-loading for routine status queries. The portal DB becomes a cache, not authoritative — manifest in git stays the source of truth.

### Subagent-per-module writing
For large labs (2+ hours, 6+ modules), isolated subagents per module could prevent context accumulation. Parked until scale is a real problem.

---

## Separate Workstreams

### AgnosticD: Split ocp4_workload_field_content
Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD apps and return immediately (no health waiting). ArgoCD eventual consistency handles operator → CR ordering. Separate workstream in the AgnosticD repo, not in PH.

---

## Completed (recent)

- **2026-04-27** — Intake simplification: 3 entry paths → 2, conversational opening for Path B, Path C merged
- **2026-04-27** — Phase-gate testing: Showroom and automation repo gates tested end-to-end; 12 issues found and fixed
- **2026-04-24** — Orchestrator discovery redesign: CWD-first, one-level subdirectory scan, project selection UI
- **2026-04-24** — Phase-gate repo creation: Orchestrator checks for Showroom/automation repos before dispatch
- **2026-04-21** — Full skills redesign: deployment modes, worklog, smart intake, git sync, phase ordering
